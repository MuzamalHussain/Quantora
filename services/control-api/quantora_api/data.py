"""MongoDB migrations and tenant-scoped persistence; no future trading CRUD API."""

import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any
from uuid import uuid4

from pymongo import ASCENDING, AsyncMongoClient
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from .security import now

Doc = dict[str, Any]
DB = AsyncDatabase[Doc]
Session = AsyncClientSession


def schema(fields: dict[str, Any], required: list[str] | None = None) -> Doc:
    props: Doc = {
        "_id": {"bsonType": "string"},
        "schema_version": {"enum": [1]},
        "created_at": {"bsonType": "date"},
        **fields,
    }
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": required or list(props),
            "additionalProperties": False,
            "properties": props,
        }
    }


S = {"bsonType": "string"}
D = {"bsonType": "date"}
SCHEMAS: dict[str, Doc] = {
    "users": schema(
        {
            "tenant_id": S,
            "email": S,
            "password_hash": S,
            "role": {"enum": ["TENANT_OWNER", "PLATFORM_ADMIN"]},
            "verified": {"bsonType": "bool"},
            "auth_version": {"bsonType": "int"},
        }
    ),
    "tenants": schema({"owner_id": S}),
    "sessions": schema(
        {
            "user_id": S,
            "token_hash": S,
            "csrf_hash": S,
            "expires_at": D,
            "auth_version": {"bsonType": "int"},
        }
    ),
    "tokens": schema(
        {
            "user_id": S,
            "token_hash": S,
            "purpose": {"enum": ["reset", "verify"]},
            "expires_at": D,
            "auth_version": {"bsonType": "int"},
        }
    ),
    "settings": schema(
        {"tenant_id": S, "theme": {"enum": ["dark", "system"]}, "timeframe": {"enum": [1, 5, 15]}}
    ),
    "credentials": schema(
        {
            "tenant_id": S,
            "owner_id": S,
            "provider": {"enum": ["BINANCE", "NEWS", "MACRO"]},
            "environment": {"enum": ["TESTNET", "LIVE", "PLATFORM"]},
            "scope": {"enum": ["TENANT", "PLATFORM"]},
            "status": {"enum": ["UNVERIFIED", "DISABLED"]},
            "revision": {"bsonType": "int"},
            "encrypted": {
                "bsonType": "object",
                "additionalProperties": False,
                "required": ["version", "key_id", "nonce", "ciphertext"],
                "properties": {
                    "version": {"enum": [1]},
                    "key_id": S,
                    "nonce": {"bsonType": "binData"},
                    "ciphertext": {"bsonType": "binData"},
                },
            },
        }
    ),
    "audit": schema(
        {
            "tenant_id": S,
            "actor_id": S,
            "action": S,
            "target": S,
            "correlation_id": S,
            "outcome": {"enum": ["SUCCESS", "DENIED", "FAILED"]},
        }
    ),
    "idempotency": schema(
        {
            "tenant_id": S,
            "operation": S,
            "key": S,
            "fingerprint": S,
            "result": {"bsonType": "object"},
        }
    ),
    "migrations": schema({"version": {"bsonType": "int"}, "checksum": S}),
    "rotations": schema(
        {"key_id": S, "state": {"enum": ["RUNNING", "COMPLETE"]}, "processed": {"bsonType": "int"}}
    ),
}
# Foundations contain references and exact decimals only, never fabricated trading effects.
for _collection in (
    "bot_sessions",
    "predictions",
    "outcomes",
    "order_intents",
    "fill_events",
    "ledger_events",
    "model_versions",
    "training_runs",
):
    SCHEMAS[_collection] = schema(
        {
            "tenant_id": S,
            "environment": S,
            "record_ref": S,
            "version_ref": S,
            "amount": {"bsonType": "decimal"},
        },
        [
            "_id",
            "schema_version",
            "created_at",
            "tenant_id",
            "environment",
            "record_ref",
            "version_ref",
        ],
    )

# name -> (fields, unique, TTL seconds or None)
INDEXES: dict[str, list[tuple[list[tuple[str, int]], bool, int | None]]] = {
    "users": [([("email", 1)], True, None), ([("tenant_id", 1)], True, None)],
    "tenants": [([("owner_id", 1)], True, None)],
    "sessions": [
        ([("token_hash", 1)], True, None),
        ([("expires_at", 1)], False, 0),
        ([("user_id", 1)], False, None),
    ],
    "tokens": [
        ([("token_hash", 1)], True, None),
        ([("expires_at", 1)], False, 0),
        ([("user_id", 1), ("purpose", 1)], False, None),
    ],
    "settings": [([("tenant_id", 1)], True, None)],
    "credentials": [
        ([("tenant_id", 1), ("provider", 1), ("environment", 1)], True, None),
        ([("encrypted.key_id", 1), ("encrypted.nonce", 1)], True, None),
    ],
    "audit": [([("tenant_id", 1), ("created_at", 1)], False, None)],
    "idempotency": [([("tenant_id", 1), ("operation", 1), ("key", 1)], True, None)],
}
for _collection in set(SCHEMAS) - set(INDEXES):
    INDEXES[_collection] = (
        []
        if _collection in ("migrations", "rotations")
        else [
            (
                [("tenant_id", ASCENDING), ("environment", ASCENDING), ("record_ref", ASCENDING)],
                True,
                None,
            )
        ]
    )


def document(**fields: Any) -> Doc:
    return {"_id": str(uuid4()), "schema_version": 1, "created_at": now(), **fields}


async def audit(
    db: DB,
    actor: Doc | None,
    action: str,
    target: str,
    cid: str,
    session: Session | None = None,
    outcome: str = "SUCCESS",
) -> None:
    # Callers use internal constant actions/targets or server-generated UUIDs only.
    await db.audit.insert_one(
        document(
            tenant_id=actor["tenant_id"] if actor else "SYSTEM",
            actor_id=actor["_id"] if actor else "SYSTEM",
            action=action,
            target=target,
            correlation_id=cid,
            outcome=outcome,
        ),
        session=session,
    )


async def transaction(db: DB, callback: Callable[[Session], Awaitable[Doc]]) -> Doc:
    async with db.client.start_session() as session:
        return await session.with_transaction(
            callback,
            read_concern=ReadConcern("snapshot"),
            write_concern=WriteConcern("majority", j=True),
            max_commit_time_ms=3000,
        )


CHECKSUM = hashlib.sha256(json.dumps([SCHEMAS, INDEXES], sort_keys=True).encode()).hexdigest()


async def migrate(db: DB, fail_after: str | None = None) -> None:
    """Sticky lock: crashes require explicit operator unlock; never steal a live migration."""
    owner = str(uuid4())
    try:
        await db.migration_lock.insert_one(
            {"_id": "exclusive", "owner": owner, "created_at": now()}
        )
    except DuplicateKeyError as exc:
        raise ValueError("Migration lock held; inspect before explicit recovery") from exc
    try:
        old = await db.migrations.find_one({"_id": "v1"})
        if old and old["checksum"] != CHECKSUM:
            raise ValueError("Migration checksum changed; create a new migration")
        names = await db.list_collection_names()
        for name, validator in SCHEMAS.items():
            if name not in names:
                await db.create_collection(
                    name, validator=validator, validationLevel="strict", validationAction="error"
                )
            else:
                options = await db[name].options()
                if options.get("validator") != validator:
                    if name == "migrations" and not options.get("validator"):
                        # A pre-v1 Phase 4 API start could create only its v2 marker.
                        # Validate every existing marker before attaching the v1 schema;
                        # collMod preserves records and is not a schema downgrade.
                        markers = await db[name].find({}).to_list(None)
                        expected_fields = {
                            "_id", "schema_version", "created_at", "version", "checksum"
                        }
                        if all(
                            set(marker) == expected_fields
                            and isinstance(marker["_id"], str)
                            and type(marker["schema_version"]) is int
                            and marker["schema_version"] == 1
                            and isinstance(marker["created_at"], datetime)
                            and type(marker["version"]) is int
                            and isinstance(marker["checksum"], str)
                            for marker in markers
                        ):
                            await db.command(
                                "collMod", name, validator=validator,
                                validationLevel="strict", validationAction="error"
                            )
                            options = await db[name].options()
                    if options.get("validator") != validator:
                        # Existing incompatible schemas are never overwritten.
                        raise ValueError("Existing collection schema differs: " + name)
            for fields, unique, ttl in INDEXES[name]:
                if unique:
                    group = {field.replace(".", "_"): "$" + field for field, _ in fields}
                    duplicates = await (
                        await db[name].aggregate(
                            [
                                {"$group": {"_id": group, "n": {"$sum": 1}}},
                                {"$match": {"n": {"$gt": 1}}},
                                {"$limit": 1},
                            ]
                        )
                    ).to_list(1)
                    if duplicates:
                        raise ValueError("Conflicting records; migration did not delete data")
                opts: Doc = {"unique": unique}
                if ttl is not None:
                    opts["expireAfterSeconds"] = ttl
                await db[name].create_index(fields, **opts)
            if fail_after == name:
                raise ValueError("Injected migration interruption")

        async def finish(session: Session) -> Doc:
            if not old:
                await db.migrations.insert_one(
                    document(_id="v1", version=1, checksum=CHECKSUM), session=session
                )
                await audit(db, None, "migration.applied", "v1", owner, session)
            return {}

        await transaction(db, finish)
    finally:
        await db.migration_lock.delete_one({"_id": "exclusive", "owner": owner})


class Repository:
    """Tenant always comes from authenticated server context. No raw client query passthrough."""

    def __init__(self, db: DB, tenant_id: str):
        self.db, self.tenant_id = db, tenant_id

    async def credentials(self) -> list[Doc]:
        return await self.db.credentials.find({"tenant_id": self.tenant_id}).limit(100).to_list(100)

    async def credential(self, identifier: str, session: Session | None = None) -> Doc | None:
        return await self.db.credentials.find_one(
            {"_id": identifier, "tenant_id": self.tenant_id}, session=session
        )

    async def summary(self) -> list[Doc]:
        cursor = await self.db.credentials.aggregate(
            [
                {"$match": {"tenant_id": self.tenant_id}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            ]
        )
        return await cursor.to_list(10)


async def idempotent(
    db: DB,
    actor: Doc,
    operation: str,
    key: str,
    payload: Doc,
    effect: Callable[[Session], Awaitable[Doc]],
) -> Doc:
    if not 8 <= len(key) <= 128:
        raise ValueError("Idempotency key required")
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    query = {"tenant_id": actor["tenant_id"], "operation": operation, "key": key}

    async def apply(session: Session) -> Doc:
        previous = await db.idempotency.find_one(query, session=session)
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise ValueError("Idempotency key payload conflict")
            result: Doc = previous["result"]
            return result
        result = await effect(session)
        await db.idempotency.insert_one(
            document(**query, fingerprint=fingerprint, result=result), session=session
        )
        return result

    try:
        return await transaction(db, apply)
    except DuplicateKeyError:
        # A concurrent winner may have committed the same key. Read only durable result.
        previous = await db.idempotency.find_one(query)
        if previous and previous["fingerprint"] == fingerprint:
            result: Doc = previous["result"]
            return result
        raise ValueError("Idempotency conflict") from None


def client(url: str) -> AsyncMongoClient[Doc]:
    return AsyncMongoClient(
        url,
        tz_aware=True,
        serverSelectionTimeoutMS=1500,
        maxPoolSize=16,
        w="majority",
        journal=True,
    )
