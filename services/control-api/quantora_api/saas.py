"""Transactional account and custody services. Public outputs are explicit allowlists."""

import asyncio
from datetime import timedelta

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from .data import CHECKSUM, DB, Doc, Repository, Session, audit, document, idempotent, transaction
from .security import (
    DUMMY_HASH,
    Custody,
    FoundationObligations,
    MailDelivery,
    SaaSConfig,
    UnconfiguredMail,
    digest,
    normalize_email,
    now,
    password_hash,
    password_matches,
    token,
)


class SaaS:
    def __init__(self, db: DB, redis: Redis, config: SaaSConfig, mail: MailDelivery | None = None):
        self.db, self.redis, self.config = db, redis, config
        self.mail = mail or UnconfiguredMail()
        self.custody = Custody(config)
        self.obligations = FoundationObligations()

    async def ready(self) -> None:
        migration = await self.db.migrations.find_one({"_id": "v1", "checksum": CHECKSUM})
        if migration is None:
            raise HTTPException(503)

    async def throttle(self, action: str, address: str, email: str = "") -> None:
        script = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n"
        try:
            for scope, suffix, maximum in [
                ("address", address, 30),
                ("account", email or address, 8),
            ]:
                key = f"{self.config.database}:abuse:{action}:{scope}:{digest(suffix)}"
                count = await self.redis.eval(script, 1, key, 60)
                if int(count) > maximum:
                    raise HTTPException(429)
        except RedisError:
            raise HTTPException(503) from None

    @staticmethod
    def public_user(user: Doc) -> Doc:
        return {k: user[k] for k in ("_id", "email", "tenant_id", "role", "verified")}

    @staticmethod
    def metadata(credential: Doc) -> Doc:
        return {
            **{
                k: credential[k]
                for k in ("_id", "provider", "environment", "scope", "status", "revision")
            },
            "masked": "••••••••",
            "connection": "UNVERIFIED",
        }

    async def register(self, email: str, password: str, cid: str, admin: bool = False) -> None:
        email = normalize_email(email)
        hashed = await asyncio.to_thread(password_hash, password)
        user = document(
            email=email,
            tenant_id=token(),
            password_hash=hashed,
            role="PLATFORM_ADMIN" if admin else "TENANT_OWNER",
            verified=False,
            auth_version=1,
        )

        async def create(session: Session) -> Doc:
            await self.db.users.insert_one(user, session=session)
            await self.db.tenants.insert_one(
                document(_id=user["tenant_id"], owner_id=user["_id"]), session=session
            )
            await self.db.settings.insert_one(
                document(tenant_id=user["tenant_id"], theme="dark", timeframe=1), session=session
            )
            await audit(
                self.db,
                user,
                "admin.bootstrap" if admin else "user.register",
                user["_id"],
                cid,
                session,
            )
            return {}

        try:
            await transaction(self.db, create)
        except DuplicateKeyError:
            if admin:
                raise ValueError("Account already exists; no role/password changed") from None
            return  # Generic public registration result prevents account enumeration.

    async def login(self, email: str, password: str, csrf: str, cid: str) -> tuple[Doc, str]:
        user = await self.db.users.find_one({"email": normalize_email(email)})
        good = await asyncio.to_thread(
            password_matches, user["password_hash"] if user else DUMMY_HASH, password
        )
        if not user or not good:
            await audit(self.db, None, "login.denied", "AUTH", cid, outcome="DENIED")
            raise HTTPException(401)
        raw = token()

        async def create(session: Session) -> Doc:
            # Optimistic auth-version write serializes login with password reset/change.
            current = await self.db.users.update_one(
                {"_id": user["_id"], "auth_version": user["auth_version"]},
                {"$inc": {"auth_version": 0}},
                session=session,
            )
            if current.matched_count != 1:
                raise HTTPException(401)
            await self.db.sessions.insert_one(
                document(
                    user_id=user["_id"],
                    token_hash=digest(raw),
                    csrf_hash=digest(csrf),
                    expires_at=now() + timedelta(seconds=self.config.session_seconds),
                    auth_version=user["auth_version"],
                ),
                session=session,
            )
            await audit(self.db, user, "login.success", user["_id"], cid, session)
            return self.public_user(user)

        return await transaction(self.db, create), raw

    async def context(self, raw: str | None) -> tuple[Doc, Doc]:
        if not raw or len(raw) > 128:
            raise HTTPException(401)
        session = await self.db.sessions.find_one(
            {"token_hash": digest(raw), "expires_at": {"$gt": now()}}
        )
        user = await self.db.users.find_one({"_id": session["user_id"]}) if session else None
        if not user or not session or user["auth_version"] != session["auth_version"]:
            raise HTTPException(401)
        return user, session

    async def revoke(
        self,
        user: Doc,
        current: Doc,
        cid: str,
        all_sessions: bool = False,
        session_id: str | None = None,
    ) -> None:
        async def apply(session: Session) -> Doc:
            query = {"user_id": user["_id"]}
            if not all_sessions:
                query["_id"] = session_id or current["_id"]
            await self.db.sessions.delete_many(query, session=session)
            if all_sessions:
                await self.db.users.update_one(
                    {"_id": user["_id"]}, {"$inc": {"auth_version": 1}}, session=session
                )
            await audit(
                self.db,
                user,
                "sessions.revoke_all" if all_sessions else "session.revoke",
                user["_id"],
                cid,
                session,
            )
            return {}

        await transaction(self.db, apply)

    async def change_password(self, user: Doc, current: str, replacement: str, cid: str) -> None:
        if not await asyncio.to_thread(password_matches, user["password_hash"], current):
            raise HTTPException(401)
        hashed = await asyncio.to_thread(password_hash, replacement)

        async def apply(session: Session) -> Doc:
            result = await self.db.users.update_one(
                {"_id": user["_id"], "auth_version": user["auth_version"]},
                {"$set": {"password_hash": hashed}, "$inc": {"auth_version": 1}},
                session=session,
            )
            if result.matched_count != 1:
                raise HTTPException(409)
            await self.db.sessions.delete_many({"user_id": user["_id"]}, session=session)
            await self.db.tokens.delete_many({"user_id": user["_id"]}, session=session)
            await audit(self.db, user, "password.changed", user["_id"], cid, session)
            return {}

        await transaction(self.db, apply)

    async def issue_token(self, email: str, purpose: str, cid: str) -> None:
        if isinstance(self.mail, UnconfiguredMail):
            raise HTTPException(503)
        user = await self.db.users.find_one({"email": normalize_email(email)})
        if not user:
            return
        raw, expires = token(), now() + timedelta(seconds=self.config.token_seconds)

        async def apply(session: Session) -> Doc:
            await self.db.tokens.delete_many(
                {"user_id": user["_id"], "purpose": purpose}, session=session
            )
            await self.db.tokens.insert_one(
                document(
                    user_id=user["_id"],
                    token_hash=digest(raw),
                    purpose=purpose,
                    expires_at=expires,
                    auth_version=user["auth_version"],
                ),
                session=session,
            )
            await audit(self.db, user, "token.issued." + purpose, user["_id"], cid, session)
            return {}

        await transaction(self.db, apply)
        # Delivery is outside the retryable transaction. No real external provider is configured.
        await self.mail.send(user["email"], purpose, raw, expires)

    async def redeem(self, raw: str, purpose: str, password: str | None, cid: str) -> None:
        hashed = await asyncio.to_thread(password_hash, password) if password is not None else None

        async def apply(session: Session) -> Doc:
            used = await self.db.tokens.find_one_and_delete(
                {"token_hash": digest(raw), "purpose": purpose, "expires_at": {"$gt": now()}},
                session=session,
            )
            if not used:
                raise HTTPException(400)
            user = await self.db.users.find_one(
                {"_id": used["user_id"], "auth_version": used["auth_version"]}, session=session
            )
            if not user:
                raise HTTPException(400)
            changes = {"password_hash": hashed} if purpose == "reset" else {"verified": True}
            update: Doc = {"$set": changes}
            if purpose == "reset":
                update["$inc"] = {"auth_version": 1}
                await self.db.sessions.delete_many({"user_id": user["_id"]}, session=session)
                await self.db.tokens.delete_many({"user_id": user["_id"]}, session=session)
            await self.db.users.update_one({"_id": user["_id"]}, update, session=session)
            await audit(self.db, user, "token.consumed." + purpose, user["_id"], cid, session)
            return {}

        await transaction(self.db, apply)

    async def save_settings(self, user: Doc, payload: Doc, key: str, cid: str) -> Doc:
        async def apply(session: Session) -> Doc:
            await self.db.settings.update_one(
                {"tenant_id": user["tenant_id"]}, {"$set": payload}, session=session
            )
            await audit(self.db, user, "settings.updated", user["_id"], cid, session)
            return payload

        return await idempotent(self.db, user, "settings.update", key, payload, apply)

    @staticmethod
    def authorize_provider(user: Doc, provider: str, environment: str) -> str:
        if (
            user["role"] == "TENANT_OWNER"
            and provider == "BINANCE"
            and environment in ("TESTNET", "LIVE")
        ):
            return "TENANT"
        if (
            user["role"] == "PLATFORM_ADMIN"
            and provider in ("NEWS", "MACRO")
            and environment == "PLATFORM"
        ):
            return "PLATFORM"
        raise HTTPException(403)

    async def credential_create(self, user: Doc, data: Doc, cid: str) -> Doc:
        scope = self.authorize_provider(user, data["provider"], data["environment"])
        if not user["verified"]:
            raise HTTPException(403)
        record = document(
            tenant_id=user["tenant_id"],
            owner_id=user["_id"],
            provider=data["provider"],
            environment=data["environment"],
            scope=scope,
            status="UNVERIFIED",
            revision=1,
        )
        record["encrypted"] = self.custody.encrypt(
            {"api_key": data["api_key"], "api_secret": data["api_secret"]}, record
        )

        async def apply(session: Session) -> Doc:
            await self.db.credentials.insert_one(record, session=session)
            await audit(self.db, user, "credential.created", record["_id"], cid, session)
            return self.metadata(record)

        try:
            return await transaction(self.db, apply)
        except DuplicateKeyError:
            raise HTTPException(409) from None

    async def credential_change(
        self, user: Doc, identifier: str, action: str, data: Doc, cid: str
    ) -> Doc:
        if not await self.obligations.safe_to_remove(user["tenant_id"], identifier):
            raise HTTPException(409)

        async def apply(session: Session) -> Doc:
            existing = await Repository(self.db, user["tenant_id"]).credential(identifier, session)
            if not existing:
                raise HTTPException(404)
            self.authorize_provider(user, existing["provider"], existing["environment"])
            if action == "remove":
                await self.db.credentials.delete_one(
                    {"_id": identifier, "tenant_id": user["tenant_id"]}, session=session
                )
            else:
                changes: Doc = {"status": "DISABLED" if action == "disable" else "UNVERIFIED"}
                if action == "replace":
                    # Verify current recoverability before replacement; wrong/missing keys fail closed.
                    self.custody.decrypt(existing["encrypted"], existing)
                    changes["encrypted"] = self.custody.encrypt(data, existing)
                await self.db.credentials.update_one(
                    {"_id": identifier, "tenant_id": user["tenant_id"]},
                    {"$set": changes, "$inc": {"revision": 1}},
                    session=session,
                )
            await audit(self.db, user, "credential." + action, identifier, cid, session)
            return {"status": "REMOVED" if action == "remove" else changes["status"]}

        return await transaction(self.db, apply)

    async def rotate(self, cid: str, stop_after: int | None = None) -> int:
        key_id = self.config.active_key
        if not key_id or key_id not in self.config.keys:
            raise ValueError("Custody unavailable")
        await self.db.rotations.update_one(
            {"_id": key_id},
            {"$setOnInsert": document(_id=key_id, key_id=key_id, state="RUNNING", processed=0)},
            upsert=True,
        )
        count = 0
        async for row in self.db.credentials.find({"encrypted.key_id": {"$ne": key_id}}):

            async def apply(session: Session, row_id: str = row["_id"]) -> Doc:
                current = await self.db.credentials.find_one({"_id": row_id}, session=session)
                if current and current["encrypted"]["key_id"] != key_id:
                    encrypted = self.custody.encrypt(
                        self.custody.decrypt(current["encrypted"], current), current
                    )
                    await self.db.credentials.update_one(
                        {"_id": current["_id"], "revision": current["revision"]},
                        {"$set": {"encrypted": encrypted}, "$inc": {"revision": 1}},
                        session=session,
                    )
                    await self.db.rotations.update_one(
                        {"_id": key_id}, {"$inc": {"processed": 1}}, session=session
                    )
                    await audit(self.db, None, "credential.rotated", current["_id"], cid, session)
                return {}

            await transaction(self.db, apply)
            count += 1
            if stop_after is not None and count >= stop_after:
                raise ValueError("Injected rotation interruption")
        await self.db.rotations.update_one({"_id": key_id}, {"$set": {"state": "COMPLETE"}})
        return count
