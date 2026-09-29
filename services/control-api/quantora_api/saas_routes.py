import secrets
from typing import Annotated, Literal

from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import PyMongoError

from .data import Doc, Repository, audit
from .saas import SaaS
from .security import digest, now, token

router = APIRouter(prefix="/api/v1/saas")


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Account(Input):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Email(Input):
    email: str = Field(min_length=3, max_length=254)


class Redeem(Input):
    token: str = Field(min_length=20, max_length=128)


class Reset(Redeem):
    password: str = Field(min_length=12, max_length=128)


class Change(Input):
    current_password: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=12, max_length=128)


class Preferences(Input):
    theme: Literal["dark", "system"]
    timeframe: Literal[1, 5, 15]


class Secret(Input):
    api_key: str = Field(min_length=1, max_length=512)
    api_secret: str = Field(min_length=1, max_length=512)


class Credential(Secret):
    provider: Literal["BINANCE", "NEWS", "MACRO"]
    environment: Literal["TESTNET", "LIVE", "PLATFORM"]


async def service(request: Request) -> SaaS:
    saas: SaaS = request.app.state.saas
    await saas.ready()
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("origin") not in saas.config.origins:
            raise HTTPException(403)
        cookie, header = (
            request.cookies.get("quantora_csrf", ""),
            request.headers.get("x-csrf-token", ""),
        )
        if len(cookie) < 32 or not secrets.compare_digest(cookie, header):
            raise HTTPException(403)
    return saas


Service = Annotated[SaaS, Depends(service)]


async def current(request: Request, saas: Service) -> tuple[Doc, Doc]:
    user, session = await saas.context(request.cookies.get(saas.config.cookie))
    if request.method not in ("GET", "HEAD", "OPTIONS") and not secrets.compare_digest(
        session["csrf_hash"], digest(request.headers.get("x-csrf-token", ""))
    ):
        raise HTTPException(403)
    return user, session


Current = Annotated[tuple[Doc, Doc], Depends(current)]


def cid(request: Request) -> str:
    return str(request.state.correlation_id)


def cookie_response(
    saas: SaaS, body: Doc, raw: str | None = None, clear: bool = False
) -> JSONResponse:
    response = JSONResponse(body)
    if raw is not None:
        response.set_cookie(
            saas.config.cookie,
            raw,
            max_age=saas.config.session_seconds,
            httponly=True,
            secure=saas.config.secure_cookie,
            samesite="lax",
            path="/",
        )
    if clear:
        response.delete_cookie(
            saas.config.cookie,
            httponly=True,
            secure=saas.config.secure_cookie,
            samesite="lax",
            path="/",
        )
    return response


@router.get("/auth/csrf")
async def csrf(request: Request, saas: Service) -> JSONResponse:
    raw = token()
    if request.cookies.get(saas.config.cookie):
        try:
            _, session = await saas.context(request.cookies[saas.config.cookie])
            await saas.db.sessions.update_one(
                {"_id": session["_id"]}, {"$set": {"csrf_hash": digest(raw)}}
            )
        except HTTPException:
            pass
    response = JSONResponse({"csrf_token": raw})
    response.set_cookie(
        "quantora_csrf",
        raw,
        secure=saas.config.secure_cookie,
        httponly=False,
        samesite="strict",
        path="/",
        max_age=saas.config.session_seconds,
    )
    return response


@router.post("/auth/register")
async def register(body: Account, request: Request, saas: Service) -> Doc:
    await saas.throttle(
        "register", request.client.host if request.client else "unknown", body.email.strip().lower()
    )
    await saas.register(body.email, body.password, cid(request))
    return {"message": "Registration processed. You may sign in if the account is available."}


@router.post("/auth/login")
async def login(body: Account, request: Request, saas: Service) -> JSONResponse:
    await saas.throttle(
        "login", request.client.host if request.client else "unknown", body.email.strip().lower()
    )
    user, raw = await saas.login(
        body.email, body.password, request.headers["x-csrf-token"], cid(request)
    )
    # New random session every login; caller-supplied session is never adopted.
    return cookie_response(saas, {"user": user}, raw)


@router.get("/auth/me")
async def me(saas: Service, context: Current) -> Doc:
    return {"user": saas.public_user(context[0])}


@router.get("/auth/sessions")
async def sessions(saas: Service, context: Current) -> Doc:
    rows = (
        await saas.db.sessions.find(
            {"user_id": context[0]["_id"], "expires_at": {"$gt": now()}},
            {"_id": 1, "expires_at": 1},
        )
        .limit(100)
        .to_list(100)
    )
    return {
        "sessions": [
            {
                "id": r["_id"],
                "expires_at": r["expires_at"].isoformat(),
                "current": r["_id"] == context[1]["_id"],
            }
            for r in rows
        ]
    }


@router.post("/auth/logout")
async def logout(request: Request, saas: Service, context: Current) -> JSONResponse:
    await saas.revoke(*context, cid(request))
    return cookie_response(saas, {"message": "Signed out"}, clear=True)


@router.post("/auth/logout-all")
async def logout_all(request: Request, saas: Service, context: Current) -> JSONResponse:
    await saas.revoke(*context, cid(request), all_sessions=True)
    return cookie_response(saas, {"message": "All sessions revoked"}, clear=True)


@router.delete("/auth/sessions/{identifier}")
async def revoke(identifier: str, request: Request, saas: Service, context: Current) -> Doc:
    await saas.revoke(*context, cid(request), session_id=identifier)
    return {"message": "Session revocation processed"}


@router.post("/auth/password")
async def password(body: Change, request: Request, saas: Service, context: Current) -> JSONResponse:
    await saas.throttle("password", context[0]["_id"])
    await saas.change_password(context[0], body.current_password, body.password, cid(request))
    return cookie_response(saas, {"message": "Password changed; sign in again"}, clear=True)


@router.post("/auth/recovery/{purpose}")
async def recovery(
    purpose: Literal["reset", "verify"], body: Email, request: Request, saas: Service
) -> Doc:
    await saas.throttle(
        "recovery", request.client.host if request.client else "unknown", body.email.strip().lower()
    )
    await saas.issue_token(body.email, purpose, cid(request))
    return {
        "message": "If eligible, a development-only delivery was created. No external email was sent."
    }


@router.post("/auth/reset")
async def reset(body: Reset, request: Request, saas: Service) -> JSONResponse:
    await saas.throttle("redeem", request.client.host if request.client else "unknown")
    await saas.redeem(body.token, "reset", body.password, cid(request))
    return cookie_response(saas, {"message": "Password reset; sign in again"}, clear=True)


@router.post("/auth/verify")
async def verify(body: Redeem, request: Request, saas: Service) -> Doc:
    await saas.throttle("redeem", request.client.host if request.client else "unknown")
    await saas.redeem(body.token, "verify", None, cid(request))
    return {"message": "Email verified by local development delivery"}


@router.get("/settings")
async def settings(saas: Service, context: Current) -> Doc:
    row = await saas.db.settings.find_one({"tenant_id": context[0]["tenant_id"]})
    if row is None:
        raise HTTPException(503)
    return {k: row[k] for k in ("theme", "timeframe")}


@router.put("/settings")
async def save_settings(
    body: Preferences, request: Request, saas: Service, context: Current
) -> Doc:
    return await saas.save_settings(
        context[0], body.model_dump(), request.headers.get("idempotency-key", ""), cid(request)
    )


@router.get("/integrations")
async def integrations(saas: Service, context: Current) -> Doc:
    return {
        "integrations": [
            saas.metadata(r)
            for r in await Repository(saas.db, context[0]["tenant_id"]).credentials()
        ]
    }


@router.get("/integrations/summary")
async def integration_summary(saas: Service, context: Current) -> Doc:
    return {"summary": await Repository(saas.db, context[0]["tenant_id"]).summary()}


@router.get("/integrations/{identifier}")
async def integration(identifier: str, saas: Service, context: Current) -> Doc:
    row = await Repository(saas.db, context[0]["tenant_id"]).credential(identifier)
    if not row:
        raise HTTPException(404)
    return saas.metadata(row)


@router.post("/integrations")
async def add_integration(
    body: Credential, request: Request, saas: Service, context: Current
) -> Doc:
    return await saas.credential_create(context[0], body.model_dump(), cid(request))


@router.put("/integrations/{identifier}")
async def replace_integration(
    identifier: str, body: Secret, request: Request, saas: Service, context: Current
) -> Doc:
    return await saas.credential_change(
        context[0], identifier, "replace", body.model_dump(), cid(request)
    )


@router.post("/integrations/{identifier}/disable")
async def disable_integration(
    identifier: str, request: Request, saas: Service, context: Current
) -> Doc:
    return await saas.credential_change(context[0], identifier, "disable", {}, cid(request))


@router.delete("/integrations/{identifier}")
async def remove_integration(
    identifier: str, request: Request, saas: Service, context: Current
) -> Doc:
    return await saas.credential_change(context[0], identifier, "remove", {}, cid(request))


@router.get("/export")
async def export(saas: Service, context: Current) -> Doc:
    # Explicit scoped development metadata export; retention/deletion policy not approved.
    return {
        "user": saas.public_user(context[0]),
        "integrations": [
            saas.metadata(r)
            for r in await Repository(saas.db, context[0]["tenant_id"]).credentials()
        ],
    }


@router.get("/admin/status")
async def admin_status(request: Request, saas: Service, context: Current) -> Doc:
    if context[0]["role"] != "PLATFORM_ADMIN":
        await audit(saas.db, context[0], "admin.denied", "ADMIN", cid(request), outcome="DENIED")
        raise HTTPException(403)
    await audit(saas.db, context[0], "admin.status", "ADMIN", cid(request))
    return {"profile": "LOCAL", "trading_enabled": False, "tenant_impersonation": False}


async def safe_failure(request: Request, exc: Exception) -> JSONResponse:
    status = 503 if isinstance(exc, (PyMongoError, InvalidTag)) else 400
    return JSONResponse(
        {
            "error": {
                "code": "UNAVAILABLE" if status == 503 else "REJECTED",
                "message": "Operation could not be completed",
            },
            "correlation_id": cid(request),
        },
        status_code=status,
    )
