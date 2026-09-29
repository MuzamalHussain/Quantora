import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from jsonschema import ValidationError

from quantora_api.app import Boundary, create_app, safe_log
from quantora_api.config import Settings
from quantora_api.contracts import parse_contract

ROOT = Path(__file__).resolve().parents[3]
CASES = json.loads((ROOT / "contracts/fixtures.json").read_text(encoding="utf-8"))
SENTINEL = "SYNTHETIC_SECRET_SENTINEL"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_contracts(case):
    raw = json.dumps(case["value"]).encode()
    if case["valid"]:
        assert parse_contract(raw) == case["value"]
    else:
        with pytest.raises((ValueError, ValidationError)):
            parse_contract(raw)


@pytest.mark.parametrize("mode", ["LIVE", "AUTO", "paper", "", "PAPER\n"])
def test_invalid_modes(mode):
    with pytest.raises(ValueError):
        Settings(mode=mode)


@pytest.mark.parametrize(
    "url",
    [
        "http://evil.example:8101",
        "http://127.0.0.1:8101/orders",
        "http://127.0.0.1:8101/?key=secret",
        "http://user:secret@127.0.0.1:8101",
    ],
)
def test_bad_config(url):
    with pytest.raises(ValueError):
        Settings(core_url=url)


def test_nonfinite_and_logger():
    with pytest.raises(ValueError):
        parse_contract(b'{"number": NaN}')
    assert SENTINEL not in safe_log(SENTINEL, SENTINEL)
    assert json.loads(safe_log("request"))["occurred_at_ms"] > 0


def test_readiness_and_shutdown_unit():
    # Explicit unit stub; this is NOT real Mongo/Redis connectivity evidence.
    state = {"core": "UP", "mongodb": "UP", "redis": "UP"}

    async def probe():
        return dict(state)

    app = create_app(probe=probe)
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        assert parse_contract(ready.content)["payload"]["trading_enabled"] is False
        state["mongodb"] = "DOWN"
        assert client.get("/health/ready").status_code == 503
        assert client.get("/health/live").status_code == 200
        app.state.stopping = True
        state["mongodb"] = "UP"
        assert client.get("/health/ready").status_code == 503
    assert app.state.dependencies.http.is_closed


def test_errors_limits_cors_and_redaction(capsys):
    with TestClient(create_app()) as client:
        for method, path, content, status in [
            ("POST", "/orders", SENTINEL, 404),
            ("POST", "/health/live", "", 405),
            ("POST", "/api/v1/foundation/ping", SENTINEL, 400),
            ("POST", "/api/v1/foundation/ping", "x" * 4097, 413),
        ]:
            response = client.request(
                method,
                path + "?key=" + SENTINEL,
                content=content,
                headers={"authorization": SENTINEL, "x-request-id": SENTINEL},
            )
            assert response.status_code == status
            assert SENTINEL not in response.text
            assert (
                parse_contract(response.content)["correlation_id"]
                == response.headers["x-request-id"]
            )
        allowed = client.get("/health/live", headers={"origin": "http://127.0.0.1:5173"})
        assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
        denied = client.get("/health/live", headers={"origin": "http://evil.example"})
        assert "access-control-allow-origin" not in denied.headers
    assert SENTINEL not in capsys.readouterr().out


async def test_chunked_limit():
    async def chunks():
        yield b"x" * 2048
        yield b"x" * 2049

    app = create_app()
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
    ):
        response = await client.post("/api/v1/foundation/ping", content=chunks())
        assert response.status_code == 413


async def test_timeout_and_backpressure():
    called = asyncio.Event()

    async def slow(scope, receive, send):
        called.set()
        await asyncio.sleep(10)

    boundary = Boundary(slow, Settings())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(boundary), base_url="http://test"
    ) as client:
        # Hold the real admission semaphore; excess requests must not queue indefinitely.
        for _ in range(32):
            await boundary.slots.acquire()
        busy = await client.get("/health/live")
        assert busy.status_code == 503
        assert not called.is_set()
        for _ in range(32):
            boundary.slots.release()
        timed_out = await client.get("/health/live")
        assert called.is_set()
        assert timed_out.status_code == 504
        assert parse_contract(timed_out.content)["payload"]["code"] == "TIMEOUT"
