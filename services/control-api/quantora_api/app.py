import asyncio
import json
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from cryptography.exceptions import InvalidTag
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from jsonschema import ValidationError
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import Settings
from .contracts import envelope, parse_contract
from .market import migrate_market
from .market import router as market_router
from .saas import SaaS
from .saas_routes import router as saas_router
from .saas_routes import safe_failure
from .security import EncryptedLocalMail, FoundationObligations, SaaSConfig

Probe = Callable[[], Awaitable[dict[str, str]]]


def safe_log(event: str, cid: str = "", status: int = 0, duration_ms: float = 0) -> str:
    safe_event = event if event in {"started", "shutdown", "request"} else "internal"
    try:
        safe_id: str | None = str(UUID(cid))
    except ValueError:
        safe_id = None
    # Allowlist records: never serialize input, URLs, headers, bodies or exception text.
    return json.dumps(
        {
            "service": "control-api",
            "event": safe_event,
            "correlation_id": safe_id,
            "occurred_at_ms": time.time_ns() // 1_000_000,
            "status": status,
            "duration_ms": round(duration_ms, 3),
        }
    )


def error(mode: str, cid: str, status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(envelope(mode, cid, "ERROR", {"code": code, "message": message}), status)


class Boundary:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings
        self.slots = asyncio.Semaphore(32)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        try:
            raw = headers.get(b"x-request-id", b"").decode("ascii")
            parsed = UUID(raw)
            cid = str(parsed) if parsed.version == 4 and len(raw) == 36 else str(uuid4())
        except (ValueError, UnicodeError):
            cid = str(uuid4())
        scope.setdefault("state", {})["correlation_id"] = cid
        started = False
        status = 500
        start = time.monotonic()

        async def traced_send(message: Message) -> None:
            nonlocal started, status
            if message["type"] == "http.response.start":
                started, status = True, message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", cid.encode()),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        async def reject(status: int, code: str, message: str) -> None:
            await error(self.settings.mode, cid, status, code, message)(scope, receive, traced_send)

        if self.slots.locked():
            await reject(503, "OVERLOADED", "Service is busy")
            return
        async with self.slots:
            try:
                async with asyncio.timeout(3):
                    data = bytearray()
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        data.extend(message.get("body", b""))
                        if len(data) > 4096:
                            await reject(413, "TOO_LARGE", "Request exceeds limit")
                            return
                        if not message.get("more_body", False):
                            break
                    delivered = False

                    async def replay() -> Message:
                        nonlocal delivered
                        if delivered:
                            return await receive()
                        delivered = True
                        return {"type": "http.request", "body": bytes(data), "more_body": False}

                    await self.app(scope, replay, traced_send)
            except TimeoutError:
                if not started:
                    await reject(504, "TIMEOUT", "Request timed out")
            except Exception:  # noqa: BLE001 -- Last-resort ASGI error firewall must not leak exception input.
                if not started:
                    await reject(500, "INTERNAL", "Internal failure")
            finally:
                print(
                    safe_log("request", cid, status, (time.monotonic() - start) * 1000), flush=True
                )


class Dependencies:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.AsyncClient(
            timeout=0.6,
            trust_env=False,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=16, max_keepalive_connections=8),
        )
        self.mongo: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(
            settings.mongo_url,
            tz_aware=True,
            serverSelectionTimeoutMS=500,
            connectTimeoutMS=500,
            socketTimeoutMS=500,
            maxPoolSize=8,
        )
        self.redis: Redis = Redis.from_url(
            settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5, max_connections=8
        )

    async def core(self) -> bool:
        response = await self.http.get(self.settings.core_url.rstrip("/") + "/health/ready")
        value = parse_contract(response.content)
        return bool(
            response.status_code == 200
            and value["mode"] == self.settings.mode
            and value["event_type"] == "HEALTH"
            and value["source"]["kind"] == "FOUNDATION"
            and value["payload"]["service"] == "trading-core"
            and value["payload"]["status"] == "READY"
        )

    async def database(self) -> bool:
        hello = await self.mongo.admin.command("hello")
        return bool(hello.get("isWritablePrimary") and hello.get("setName") == "quantora-rs")

    async def cache(self) -> bool:
        return bool(await self.redis.ping())

    async def status(self) -> dict[str, str]:
        async def bounded(call: Callable[[], Awaitable[bool]]) -> str:
            try:
                async with asyncio.timeout(0.8):
                    return "UP" if await call() else "DOWN"
            except (
                TimeoutError,
                httpx.HTTPError,
                PyMongoError,
                RedisError,
                ValueError,
                ValidationError,
            ):
                return "DOWN"

        results = await asyncio.gather(
            *(bounded(f) for f in [self.core, self.database, self.cache])
        )
        return dict(zip(["core", "mongodb", "redis"], results, strict=True))

    async def close(self) -> None:
        await self.http.aclose()
        await self.mongo.close()
        await self.redis.aclose()


def create_app(
    settings: Settings | None = None,
    probe: Probe | None = None,
    saas_config: SaaSConfig | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    saas_config = saas_config or SaaSConfig.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        deps = Dependencies(settings)
        app.state.dependencies = deps
        app.state.saas = SaaS(deps.mongo[saas_config.database], deps.redis, saas_config)
        await migrate_market(app.state.saas.db)
        # This explicit grant is tied to the current schema's disabled execution contract.
        # Changing the schema to allow execution must provide a reconciled obligation checker.
        contract = json.loads(
            (
                Path(__file__).resolve().parents[3] / "contracts/foundation-v1.schema.json"
            ).read_text()
        )
        disabled = (
            contract["definitions"]["Health"]["properties"]["trading_enabled"].get("const") is False
        )
        app.state.saas.obligations = FoundationObligations(False if disabled else None)
        mailbox = os.getenv("QUANTORA_LOCAL_MAIL_DIR")
        if mailbox:
            app.state.saas.mail = EncryptedLocalMail(saas_config, Path(mailbox))
        app.state.stopping = False
        print(safe_log("started"), flush=True)
        try:
            yield
        finally:
            app.state.stopping = True
            await deps.close()
            print(safe_log("shutdown"), flush=True)

    app = FastAPI(
        title="Quantora Foundation",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(Boundary, settings=settings)
    app.include_router(saas_router)
    app.include_router(market_router)
    for exception in (ValueError, PyMongoError, InvalidTag):
        app.add_exception_handler(exception, safe_failure)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["content-type", "x-request-id"],
        expose_headers=["x-request-id"],
        allow_credentials=False,
    )

    def health(cid: str, status: str, dependencies: dict[str, str]) -> dict[str, Any]:
        return envelope(
            settings.mode,
            cid,
            "HEALTH",
            {
                "service": "control-api",
                "status": status,
                "profile": "FOUNDATION",
                "trading_enabled": False,
                "dependencies": dependencies,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        if request.url.path.startswith("/api/v1/saas/"):
            labels = {
                400: "Request rejected",
                401: "Sign in required or credentials invalid",
                403: "Operation not permitted",
                404: "Resource unavailable",
                409: "Operation conflicts with current state",
                429: "Too many attempts; try later",
                503: "Service unavailable",
            }
            return JSONResponse(
                {
                    "error": {
                        "code": str(exc.status_code),
                        "message": labels.get(exc.status_code, "Request rejected"),
                    },
                    "correlation_id": request.state.correlation_id,
                },
                exc.status_code,
            )
        code, message = (
            ("METHOD_NOT_ALLOWED", "Method is unavailable")
            if exc.status_code == 405
            else ("NOT_FOUND", "Route is unavailable")
        )
        return error(settings.mode, request.state.correlation_id, exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(
            settings.mode, request.state.correlation_id, 400, "INVALID_REQUEST", "Request rejected"
        )

    @app.get("/health/live")
    async def live(request: Request) -> dict[str, Any]:
        return health(
            request.state.correlation_id,
            "UP",
            dict.fromkeys(["core", "mongodb", "redis"], "NOT_REQUIRED"),
        )

    @app.get("/health/ready")
    @app.get("/api/v1/foundation/status")
    async def ready(request: Request) -> JSONResponse:
        deps = await (probe() if probe else app.state.dependencies.status())
        ok = not app.state.stopping and all(v == "UP" for v in deps.values())
        return JSONResponse(
            health(request.state.correlation_id, "READY" if ok else "NOT_READY", deps),
            status_code=200 if ok else 503,
        )

    @app.post("/api/v1/foundation/ping")
    async def ping(request: Request) -> JSONResponse:
        cid = request.state.correlation_id
        try:
            value = parse_contract(await request.body())
            if value["event_type"] != "PING" or value["mode"] != settings.mode:
                raise ValueError("Invalid ping")
        except (ValueError, UnicodeError, ValidationError):
            return error(settings.mode, cid, 400, "INVALID_REQUEST", "Request rejected")
        try:
            response = await app.state.dependencies.http.post(
                settings.core_url.rstrip("/") + "/api/v1/foundation/ping",
                json=value,
                headers={"x-request-id": cid},
            )
            payload = parse_contract(response.content)
            if (
                response.status_code != 200
                or payload["event_type"] != "HEALTH"
                or payload["mode"] != settings.mode
                or payload["source"]["kind"] != "FOUNDATION"
                or payload["payload"]["service"] != "trading-core"
                or payload["payload"]["status"] != "READY"
            ):
                raise ValueError("Invalid upstream response")
            return JSONResponse(payload)
        except (httpx.HTTPError, ValueError, ValidationError):
            return error(settings.mode, cid, 503, "NOT_READY", "Dependencies unavailable")

    return app
