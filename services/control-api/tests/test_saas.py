"""Real replica-set/Redis integration. Every database and Redis prefix is test-owned."""

import asyncio
import dataclasses
import json
import secrets
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from cryptography.exceptions import InvalidTag
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, OperationFailure
from redis.asyncio import Redis

from quantora_api.app import create_app
from quantora_api.backup import backup, restore
from quantora_api.config import Settings
from quantora_api.data import CHECKSUM, client, document, migrate, transaction
from quantora_api.saas import SaaS
from quantora_api.saas_routes import cookie_response
from quantora_api.security import (
    Custody,
    EncryptedLocalMail,
    FoundationObligations,
    LocalMail,
    SaaSConfig,
    decimal128,
    digest,
    now,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import scripts.phase04_collector as market_collector
from scripts.phase04_collector import (
    LeaseLost,
    MarketProcessor,
    Store,
    backfill,
    poll_oi_funding,
    save_candle,
)
from scripts.phase04_collector import request as market_request
from scripts.phase04_collector import stream as market_stream

PASSWORD = "Synthetic-test-password-73!"
SECRET = "SYNTHETIC_CREDENTIAL_DO_NOT_LEAK_73821"
BASE = "/api/v1/saas"


def test_rust_market_processor_normalization_and_book_recovery():
    binary=Path(__file__).resolve().parents[2]/"trading-core/target/debug/market_processor.exe"
    requests=[
        {"op":"instrument","value":{"symbol":"BTCUSDT","status":"TRADING","contractType":"PERPETUAL","quoteAsset":"USDT","marginAsset":"USDT","onboardDate":1,"filters":[{"filterType":"PRICE_FILTER","tickSize":"0.01"},{"filterType":"LOT_SIZE","stepSize":"0.001"}]}},
        {"op":"book_snapshot","epoch":1,"value":{"lastUpdateId":100,"bids":[["99.0000000000000001","1"]],"asks":[["102","1"]]}},
        {"op":"book_delta","epoch":1,"value":{"U":90,"u":99,"pu":0,"b":[],"a":[]}},
        {"op":"book_delta","epoch":1,"value":{"U":99,"u":101,"pu":0,"b":[["100","1"]],"a":[]}},
        {"op":"book_delta","epoch":1,"value":{"U":102,"u":102,"pu":101,"b":[["99.0000000000000001","0.00000000"]],"a":[["101.5","2"]]}},
        {"op":"book_delta","epoch":1,"value":{"U":103,"u":103,"pu":100,"b":[],"a":[]}},
        {"op":"book_snapshot","epoch":2,"value":{"lastUpdateId":200,"bids":[["101","1"]],"asks":[["102","1"]]}},
        {"op":"book_delta","epoch":2,"value":{"U":200,"u":201,"pu":0,"b":[],"a":[["100","1"]]}},
        {"op":"agg_trade","value":{"s":"BTCUSDT","T":42,"a":10,"p":"100","q":"0.1"}},
    ]
    output=subprocess.run([str(binary)],input="\n".join(json.dumps(x) for x in requests)+"\n",text=True,capture_output=True,check=True,timeout=5)
    rows=[json.loads(line) for line in output.stdout.splitlines()]
    assert len(rows)==len(requests)
    assert rows[0]["eligible"] is True
    assert rows[2]["applied"] is False
    assert rows[3]["valid"] is True and rows[3]["best_bid"]=="100"
    assert rows[4]["valid"] is True and rows[4]["bid_levels"]==1
    assert rows[5]["ok"] is False and rows[5]["error"]=="sequence gap"
    assert rows[7]["ok"] is False and rows[7]["error"]=="crossed book"
    assert rows[8]["semantics"]=="AGGREGATE_TRADE"


@pytest.mark.asyncio
async def test_continuous_public_rest_recovers_after_transient_dns_errors(world):
    _, saas, _ = world
    store = Store(saas.db, "retry-test")
    store.continuous = True
    calls = 0

    def exchange(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls <= 4:
            raise httpx.ConnectError("transient DNS failure", request=request)
        return httpx.Response(200, json={"serverTime": 1})

    async with httpx.AsyncClient(transport=httpx.MockTransport(exchange)) as http:
        assert await market_request(store, http, "/fapi/v1/time") == {"serverTime": 1}
    assert calls == 5


@pytest.mark.asyncio
async def test_market_rate_recovery_uses_local_fake_transport(world):
    _, saas, _ = world
    from quantora_api.market import migrate_market
    await migrate_market(saas.db)
    store=Store(saas.db,"rate-test")
    calls=0
    def exchange(_:httpx.Request)->httpx.Response:
        nonlocal calls
        calls+=1
        if calls==1: return httpx.Response(429,headers={"Retry-After":"1"})
        if calls==2: return httpx.Response(503)
        if calls==3: return httpx.Response(200,json={"ok":True},headers={"x-mbx-used-weight-1m":"17"})
        return httpx.Response(418,headers={"Retry-After":"120"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(exchange)) as http:
        assert await market_request(store,http,"/fapi/v1/openInterest",{"symbol":"BTCUSDT"})=={"ok":True}
        assert calls==3 and store.budget.used>=17
        with pytest.raises(RuntimeError,match="provider ban"):
            await market_request(store,http,"/fapi/v1/openInterest",{"symbol":"BTCUSDT"})
    cooldown=await saas.db.market_checkpoints.find_one({"_id":"rate:binance-usdm"})
    assert cooldown and cooldown["cooldown_until"]>now()+timedelta(seconds=100)


@pytest.mark.asyncio
async def test_market_fake_stream_snapshot_bridge_and_persistence(world,monkeypatch):
    app, saas, _ = world
    from quantora_api.market import migrate_market
    await migrate_market(saas.db)
    store=Store(saas.db,"stream-test")
    await store.acquire()
    store.processor=await MarketProcessor.start()
    events=[
        ("market",{"id":1,"result":None}),
        ("public",{"id":2,"result":None}),
        ("public",{"e":"depthUpdate","E":100,"U":100,"u":101,"pu":99,"b":[["100","1"]],"a":[]}),
        ("market",{"e":"kline","E":101,"s":"BTCUSDT","k":{"i":"1m","t":0,"T":59_999,"o":"100","h":"101","l":"99","c":"100","v":"1","x":True}}),
        ("market",{"e":"markPriceUpdate","E":102,"s":"BTCUSDT","p":"100","i":"100","r":"0.0001","T":1000}),
        ("market",{"e":"aggTrade","s":"BTCUSDT","T":103,"a":1,"p":"100","q":"1"}),
    ]
    class FakeProcess:
        def __init__(self):
            self.stdout=asyncio.StreamReader();self.stderr=asyncio.StreamReader();self.returncode=0
            for route,value in events: self.stdout.feed_data((json.dumps({"route":route,"received_at_ms":1000,"value":value})+'\n').encode())
            self.stdout.feed_eof();self.stderr.feed_eof()
        async def wait(self): return 0
        def terminate(self): self.returncode=0
    async def fake_process(*_args,**_kwargs): return FakeProcess()
    monkeypatch.setattr(asyncio,"create_subprocess_exec",fake_process)
    def exchange(request:httpx.Request)->httpx.Response:
        assert request.url.path.endswith('/depth')
        return httpx.Response(200,json={"lastUpdateId":100,"bids":[["99","1"]],"asks":[["102","1"]]})
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(exchange)) as http:
            counts=await market_stream(store,http,"BTCUSDT",1)
        assert all(counts[k]>0 for k in ("depth","kline","mark","trade"))
        book=await saas.db.market_observations.find_one({"kind":"BOOK"})
        assert book and book["valid"] is True and book["last_update_id"]==101 and book["best_bid"]=="100"
        assert await saas.db.market_candles.count_documents({"source":"BINANCE_WS"})==1
        quality=await saas.db.market_quality.find_one({"channel":"STREAM"},sort=[("recorded_at",-1)])
        assert quality and quality["state"]=="DISCONNECTED"
        browser_http=await account(app,saas,"market-stream@example.test")
        response=await browser_http.get("/api/v1/market/snapshot",params={"symbol":"BTCUSDT"})
        assert response.status_code==200
        assert response.json()["public_feed_state"]=="DISCONNECTED"
        assert response.json()["book_current"] is False
        events[:]=[("market",{"id":1,"result":None}),("public",{"id":2,"result":None})]+[("public",{"e":"depthUpdate","E":100,"U":100,"u":101,"pu":99,"b":[["100","1"]],"a":[]}) for _ in range(50)]
        monkeypatch.setattr(market_collector,"QUEUE_LIMIT",1)
        async with httpx.AsyncClient(transport=httpx.MockTransport(exchange)) as overflow_http:
            with pytest.raises(RuntimeError,match="bounded queue overflow"):
                await market_stream(store,overflow_http,"BTCUSDT",1)
        assert await saas.db.market_quality.count_documents({"channel":"STREAM","state":"INVALID"})>0
    finally:
        await store.processor.close()
        await store.release()


@pytest_asyncio.fixture
async def world():
    cfg = SaaSConfig(
        database="quantora_test_" + uuid4().hex,
        keys={"k1": secrets.token_bytes(32)},
        active_key="k1",
    )
    mongo = client(Settings().mongo_url)
    db = mongo[cfg.database]
    assert (await mongo.admin.command("hello"))["setName"] == "quantora-rs"
    await migrate(db)
    app = create_app(saas_config=cfg)
    async with app.router.lifespan_context(app):
        saas = app.state.saas
        saas.mail = LocalMail()
        assert await saas.redis.ping()
        yield app, saas, cfg
        keys = [key async for key in saas.redis.scan_iter(match=cfg.database + ":*")]
        if keys:
            await saas.redis.delete(*keys)
    assert db.name.startswith("quantora_test_")
    await mongo.drop_database(db.name)
    await mongo.close()


async def browser(app):
    http = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:4173",
        headers={"origin": "http://127.0.0.1:4173"},
    )
    csrf = await http.get(BASE + "/auth/csrf")
    assert csrf.status_code == 200
    http.headers["x-csrf-token"] = csrf.json()["csrf_token"]
    return http


async def account(app, saas, email="one@example.test", admin=False):
    http = await browser(app)
    if admin:
        await saas.register(email, PASSWORD, str(uuid4()), admin=True)
    else:
        assert (
            await http.post(BASE + "/auth/register", json={"email": email, "password": PASSWORD})
        ).status_code == 200
    result = await http.post(BASE + "/auth/login", json={"email": email, "password": PASSWORD})
    assert result.status_code == 200, result.text
    await saas.issue_token(email, "verify", str(uuid4()))
    raw = saas.mail.messages[(email, "verify")][0]
    assert (await http.post(BASE + "/auth/verify", json={"token": raw})).status_code == 200
    return http


@pytest.mark.asyncio
async def test_market_migration_idempotency_and_authenticated_bounded_reads(world):
    app, saas, _ = world
    http = await account(app, saas, "market@example.test")
    instrument = {
        "venue": "BINANCE_USDM", "symbol": "BTCUSDT", "status": "TRADING",
        "eligible": True, "tick_size": "0.10", "step_size": "0.001",
        "metadata_version": "fixture-v1", "stale": False,
    }
    await saas.db.market_instruments.update_one(
        {"venue": "BINANCE_USDM", "symbol": "BTCUSDT"}, {"$set": instrument}, upsert=True
    )
    result = await http.get("/api/v1/market/instruments")
    assert result.status_code == 200 and result.json()["items"] == [instrument]
    assert (await http.get("/api/v1/market/candles", params={"symbol":"BTCUSDT","interval":"1m","start_ms":0,"end_ms":201*86_400_000})).status_code == 400
    anonymous = await browser(app)
    assert (await anonymous.get("/api/v1/market/instruments")).status_code == 401
    await saas.db.market_instruments.update_one(
        {"venue": "BINANCE_USDM", "symbol": "BTCUSDT"}, {"$set": instrument}, upsert=True
    )
    assert await saas.db.market_instruments.count_documents({"symbol": "BTCUSDT"}) == 1


@pytest.mark.asyncio
async def test_market_collector_fenced_single_owner_and_safe_takeover(world):
    _, saas, _ = world
    first, second = Store(saas.db, "owner-one"), Store(saas.db, "owner-two")
    await first.acquire(30)
    with pytest.raises(LeaseLost):
        await second.acquire(30)
    await saas.db.market_checkpoints.update_one(
        {"_id": "collector:binance-usdm", "owner": "owner-one"},
        {"$set": {"lease_until": now() - timedelta(seconds=1)}},
    )
    await second.acquire(30)
    assert second.fence > first.fence
    with pytest.raises(LeaseLost):
        await first.renew()
    with pytest.raises(LeaseLost):
        await first.mutate("market_quality","insert_one",{"venue":"BINANCE_USDM","symbol":"BTCUSDT","channel":"TEST","state":"INVALID"})
    assert await saas.db.market_quality.count_documents({"channel":"TEST"})==0
    await second.mutate("market_quality","insert_one",{"venue":"BINANCE_USDM","symbol":"BTCUSDT","channel":"TEST","state":"LIVE"})
    assert await saas.db.market_quality.count_documents({"channel":"TEST","state":"LIVE"})==1
    await second.release()


@pytest.mark.asyncio
async def test_market_backfill_checkpoint_corrections_and_public_rest_poll(world):
    _, saas, _ = world
    from quantora_api.market import migrate_market
    await migrate_market(saas.db)
    store = Store(saas.db, "fixture-owner")
    await store.acquire()
    minute = int(time.time()*1000)//60_000*60_000
    closed = [minute-60_000,"1","2","1","2","3",minute-1]
    forming = [minute,"2","3","2","3","4",minute+59_999]

    def exchange(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/klines'):
            start = int(request.url.params['startTime'])
            return httpx.Response(200,json=[r for r in (closed,forming) if r[0]>=start])
        if request.url.path.endswith('/openInterest'):
            return httpx.Response(200,json={"symbol":"BTCUSDT","openInterest":"42.5","time":minute})
        if request.url.path.endswith('/fundingRate'):
            return httpx.Response(200,json=[{"symbol":"BTCUSDT","fundingTime":minute-60_000,"fundingRate":"0.0001"}])
        raise AssertionError(request.url)

    async with httpx.AsyncClient(transport=httpx.MockTransport(exchange)) as http:
        assert await backfill(store,http,"BTCUSDT","1m",minute-60_000,minute+1)==2
        checkpoint=await saas.db.market_checkpoints.find_one({"_id":"backfill:BTCUSDT:1m"})
        assert checkpoint["next_ms"]==minute  # Forming bar must be revisited after restart.
        assert await backfill(store,http,"BTCUSDT","1m",minute-60_000,minute+1)==1
        assert await saas.db.market_candles.count_documents({"symbol":"BTCUSDT"})==2
        assert await poll_oi_funding(store,http,"BTCUSDT")=={"open_interest":1,"settled_funding":1}
        assert await saas.db.market_observations.count_documents({"kind":"OPEN_INTEREST"})==1
        assert await saas.db.market_observations.count_documents({"kind":"SETTLED_FUNDING"})==1

    corrected={"venue":"BINANCE_USDM","symbol":"BTCUSDT","interval":"1m","open_time_ms":minute-60_000,"close_time_ms":minute-1,"open":"1","high":"2","low":"1","close":"1.5","volume":"3","closed":True,"source":"BINANCE_REST","received_at_ms":minute}
    await save_candle(store,corrected)
    assert await saas.db.market_raw_events.count_documents({"kind":"CANDLE_CORRECTION"})==1
    await store.release()
    await save_candle(store,corrected)
    assert await saas.db.market_raw_events.count_documents({"kind":"CANDLE_CORRECTION"})==1


@pytest.mark.asyncio
async def test_auth_cookie_csrf_fixation_and_sessions(world):
    app, saas, cfg = world
    http = await account(app, saas)
    raw = http.cookies.get(cfg.cookie)
    assert raw and raw not in json.dumps(await saas.db.sessions.find_one({}), default=str)
    login = await http.post(
        BASE + "/auth/login", json={"email": "one@example.test", "password": PASSWORD}
    )
    assert http.cookies.get(cfg.cookie) != raw
    assert (
        "HttpOnly" in login.headers["set-cookie"] and "SameSite=lax" in login.headers["set-cookie"]
    )
    secure = cookie_response(
        SaaS(saas.db, saas.redis, dataclasses.replace(cfg, secure_cookie=True)), {}, "synthetic"
    )
    assert "__Host-" in secure.headers["set-cookie"] and "Secure" in secure.headers["set-cookie"]
    assert (await http.get(BASE + "/auth/me")).status_code == 200
    assert (
        await http.post(BASE + "/auth/logout", headers={"x-csrf-token": "forged"})
    ).status_code == 403
    assert (
        await http.post(BASE + "/auth/logout", headers={"origin": "https://evil.example"})
    ).status_code == 403
    listed = (await http.get(BASE + "/auth/sessions")).json()["sessions"]
    other = next(s for s in listed if not s["current"])
    assert (await http.delete(BASE + "/auth/sessions/" + other["id"])).status_code == 200
    with pytest.raises(HTTPException):
        await saas.context(raw)
    assert (await http.post(BASE + "/auth/logout-all")).status_code == 200
    assert (await http.get(BASE + "/auth/me")).status_code == 401
    await http.aclose()


@pytest.mark.asyncio
async def test_duplicate_registration_and_invalid_login(world):
    app, saas, _ = world
    http = await browser(app)
    payload = {"email": " Race@Example.Test ", "password": PASSWORD}
    results = await asyncio.gather(
        *(http.post(BASE + "/auth/register", json=payload) for _ in range(3))
    )
    assert all(r.status_code == 200 for r in results)
    assert await saas.db.users.count_documents({"email": "race@example.test"}) == 1
    assert await saas.db.tenants.count_documents({}) == 1
    assert (
        await http.post(BASE + "/auth/register", json={**payload, "role": "PLATFORM_ADMIN"})
    ).status_code == 400
    assert (
        await http.post(BASE + "/auth/login", json={**payload, "password": "wrong"})
    ).status_code == 401
    with pytest.raises(ValueError):
        await saas.register("race@example.test", PASSWORD, str(uuid4()), admin=True)
    assert (await saas.db.users.find_one({}))["role"] == "TENANT_OWNER"
    await http.aclose()


@pytest.mark.asyncio
async def test_recovery_expiry_concurrent_consumption_and_password_policy(world):
    app, saas, cfg = world
    http = await account(app, saas)
    old = http.cookies.get(cfg.cookie)
    response = await http.post(BASE + "/auth/recovery/reset", json={"email": "one@example.test"})
    raw = saas.mail.messages[("one@example.test", "reset")][0]
    assert raw not in response.text
    assert raw not in json.dumps(await saas.db.tokens.find_one({}), default=str)
    results = await asyncio.gather(
        *(
            http.post(BASE + "/auth/reset", json={"token": raw, "password": PASSWORD + "new"})
            for _ in range(2)
        )
    )
    assert sorted(r.status_code for r in results) == [200, 400]
    with pytest.raises(HTTPException):
        await saas.context(old)
    await saas.issue_token("one@example.test", "reset", str(uuid4()))
    expired = saas.mail.messages[("one@example.test", "reset")][0]
    await saas.db.tokens.update_one(
        {"token_hash": digest(expired)}, {"$set": {"expires_at": now() - timedelta(seconds=1)}}
    )
    assert (
        await http.post(BASE + "/auth/reset", json={"token": expired, "password": PASSWORD})
    ).status_code == 400
    assert (
        await http.post(
            BASE + "/auth/login", json={"email": "one@example.test", "password": PASSWORD + "new"}
        )
    ).status_code == 200
    assert (
        await http.post(
            BASE + "/auth/password", json={"current_password": "incorrect", "password": PASSWORD}
        )
    ).status_code == 401
    assert (
        await http.post(
            BASE + "/auth/password",
            json={"current_password": PASSWORD + "new", "password": PASSWORD},
        )
    ).status_code == 200
    assert (await http.get(BASE + "/auth/me")).status_code == 401
    await http.aclose()


@pytest.mark.asyncio
async def test_tenant_roles_credentials_and_secret_leaks(world, capsys):
    app, saas, _ = world
    one, two, admin = (
        await account(app, saas),
        await account(app, saas, "two@example.test"),
        await account(app, saas, "admin@example.test", True),
    )
    payload = {
        "provider": "BINANCE",
        "environment": "TESTNET",
        "api_key": SECRET,
        "api_secret": SECRET,
    }
    added = await one.post(BASE + "/integrations", json=payload)
    assert added.status_code == 200, added.text
    identifier = added.json()["_id"]
    row = await saas.db.credentials.find_one({"_id": identifier})
    assert SECRET not in json.dumps(row, default=str)
    assert saas.custody.decrypt(row["encrypted"], row)["api_secret"] == SECRET
    for method, path, body in [
        ("get", "/integrations/" + identifier, None),
        ("put", "/integrations/" + identifier, {"api_key": SECRET, "api_secret": SECRET}),
        ("delete", "/integrations/" + identifier, None),
    ]:
        response = await two.request(method, BASE + path, json=body)
        assert response.status_code == 404
    assert (await two.get(BASE + "/integrations?tenant_id=" + row["tenant_id"])).json()[
        "integrations"
    ] == []
    assert (await two.get(BASE + "/integrations/summary")).json()["summary"] == []
    assert (await two.get(BASE + "/export")).json()["integrations"] == []
    assert (await one.get(BASE + "/admin/status")).status_code == 403
    assert (await admin.get(BASE + "/admin/status")).status_code == 200
    assert (await admin.get(BASE + "/integrations/" + identifier)).status_code == 404
    assert (
        await one.post(
            BASE + "/integrations", json={**payload, "provider": "NEWS", "environment": "PLATFORM"}
        )
    ).status_code == 403
    assert (
        await admin.post(
            BASE + "/integrations", json={**payload, "provider": "NEWS", "environment": "PLATFORM"}
        )
    ).status_code == 200
    replaced = await one.put(
        BASE + "/integrations/" + identifier,
        json={"api_key": SECRET + "2", "api_secret": SECRET + "2"},
    )
    assert replaced.status_code == 200 and SECRET not in replaced.text
    assert (await one.post(BASE + "/integrations/" + identifier + "/disable")).json()[
        "status"
    ] == "DISABLED"
    saas.obligations = FoundationObligations(True)
    assert (await one.delete(BASE + "/integrations/" + identifier)).status_code == 409
    saas.obligations = FoundationObligations(False)
    assert (await one.delete(BASE + "/integrations/" + identifier)).status_code == 200
    for http in (one, two, admin):
        assert SECRET not in (await http.get(BASE + "/export")).text
        await http.aclose()
    assert SECRET not in json.dumps(await saas.db.audit.find({}).to_list(None), default=str)
    assert SECRET not in capsys.readouterr().out


@pytest.mark.asyncio
async def test_custody_tamper_swap_rotation_and_restore(world, tmp_path):
    app, saas, cfg = world
    http = await account(app, saas)
    payload = {
        "provider": "BINANCE",
        "environment": "TESTNET",
        "api_key": SECRET,
        "api_secret": SECRET,
    }
    await http.post(BASE + "/integrations", json=payload)
    await http.post(BASE + "/integrations", json={**payload, "environment": "LIVE"})
    row = await saas.db.credentials.find_one({})
    for changed in (
        {**row, "tenant_id": "other"},
        {**row, "environment": "LIVE" if row["environment"] == "TESTNET" else "TESTNET"},
    ):
        with pytest.raises(InvalidTag):
            saas.custody.decrypt(row["encrypted"], changed)
    with pytest.raises(InvalidTag):
        Custody(dataclasses.replace(cfg, keys={"k1": secrets.token_bytes(32)})).decrypt(
            row["encrypted"], row
        )
    with pytest.raises(ValueError):
        Custody(SaaSConfig()).decrypt(row["encrypted"], row)
    with pytest.raises(InvalidTag):
        saas.custody.decrypt({**row["encrypted"], "ciphertext": bytes(32)}, row)
    rotated = dataclasses.replace(
        cfg, keys={**cfg.keys, "k2": secrets.token_bytes(32)}, active_key="k2"
    )
    worker = SaaS(saas.db, saas.redis, rotated)
    with pytest.raises(ValueError):
        await worker.rotate(str(uuid4()), stop_after=1)
    assert (await saas.db.rotations.find_one({"_id": "k2"}))["state"] == "RUNNING"
    assert await worker.rotate(str(uuid4())) == 1
    assert await worker.rotate(str(uuid4())) == 0
    assert await saas.db.credentials.count_documents({"encrypted.key_id": "k2"}) == 2
    path = tmp_path / "synthetic.qbackup"
    await backup(saas.db, path, rotated, quiescent=True)
    assert SECRET.encode() not in path.read_bytes()
    target = saas.db.client["quantora_restore_" + uuid4().hex]
    try:
        evidence = await restore(path, target, rotated)
        assert evidence["decrypted_credentials"] == 2
        with pytest.raises(ValueError):
            await restore(path, target, rotated)
    finally:
        await saas.db.client.drop_database(target.name)
    await http.aclose()


@pytest.mark.asyncio
async def test_transactions_idempotency_audit_rollback_and_indexes(world):
    app, saas, _ = world
    http = await account(app, saas)
    key = str(uuid4())
    payload = {"theme": "system", "timeframe": 5}
    results = await asyncio.gather(
        *(
            http.put(BASE + "/settings", json=payload, headers={"idempotency-key": key})
            for _ in range(3)
        )
    )
    assert all(r.status_code == 200 for r in results)
    assert await saas.db.idempotency.count_documents({}) == 1
    assert await saas.db.audit.count_documents({"action": "settings.updated"}) == 1
    assert (
        await http.put(
            BASE + "/settings", json={**payload, "timeframe": 15}, headers={"idempotency-key": key}
        )
    ).status_code == 400

    async def fail(session):
        await saas.db.settings.update_one({}, {"$set": {"timeframe": 15}}, session=session)
        # Actual Mongo schema rejection at the audit sink forces transaction rollback.
        await saas.db.audit.insert_one({"_id": str(uuid4())}, session=session)
        return {}

    with pytest.raises(OperationFailure):
        await transaction(saas.db, fail)
    assert (await saas.db.settings.find_one({}))["timeframe"] == 5
    user = await saas.db.users.find_one({})
    with pytest.raises(DuplicateKeyError):
        await saas.db.users.insert_one({**user, "_id": str(uuid4())})
    await http.aclose()


@pytest.mark.asyncio
async def test_v2_market_marker_before_v1_migration_is_preserved(world):
    _, saas, _ = world
    from quantora_api.market import migrate_market

    separate = saas.db.client["quantora_test_" + uuid4().hex]
    try:
        await migrate_market(separate)
        assert await separate.migrations.count_documents({"_id": "v2-market"}) == 1
        await migrate(separate)
        assert await separate.migrations.count_documents({}) == 2
        assert (await separate.migrations.options()).get("validator")
        await migrate(separate)
        assert await separate.migrations.count_documents({}) == 2
    finally:
        await saas.db.client.drop_database(separate.name)


@pytest.mark.asyncio
async def test_migration_repeat_failure_lock_and_schema(world):
    _, saas, _ = world
    await migrate(saas.db)
    assert await saas.db.migrations.count_documents({"_id": "v1"}) == 1
    assert (await saas.db.migrations.find_one({}))["checksum"] == CHECKSUM
    await saas.db.migration_lock.insert_one({"_id": "exclusive", "owner": "test-owned"})
    with pytest.raises(ValueError):
        await migrate(saas.db)
    await saas.db.migration_lock.delete_one({"_id": "exclusive", "owner": "test-owned"})
    separate = saas.db.client["quantora_test_" + uuid4().hex]
    try:
        with pytest.raises(ValueError):
            await migrate(separate, fail_after="users")
        assert await separate.migrations.count_documents({}) == 0
        await migrate(separate)
        assert await separate.migrations.count_documents({}) == 1
        # Demonstrate uniqueness preflight against conflicting records, never deletion.
        await separate.users.drop_index("email_1")
        user = document(
            tenant_id="a",
            email="conflict@example.test",
            password_hash="test-only",
            role="TENANT_OWNER",
            verified=False,
            auth_version=1,
        )
        await separate.users.insert_many([user, {**user, "_id": str(uuid4()), "tenant_id": "b"}])
        with pytest.raises(ValueError):
            await migrate(separate)
        assert await separate.users.count_documents({}) == 2
        await separate.command("collMod", "users", validator={})
        with pytest.raises(ValueError):
            await migrate(separate)
    finally:
        await saas.db.client.drop_database(separate.name)


@pytest.mark.asyncio
async def test_expiry_rate_limit_redis_outage_and_decimals(world):
    app, saas, cfg = world
    http = await account(app, saas)
    await saas.db.sessions.update_many({}, {"$set": {"expires_at": now() - timedelta(seconds=1)}})
    assert (await http.get(BASE + "/auth/me")).status_code == 401
    results = [
        await http.post(
            BASE + "/auth/login", json={"email": "absent@example.test", "password": "wrong"}
        )
        for _ in range(9)
    ]
    assert results[-1].status_code == 429
    unavailable = Redis.from_url("redis://127.0.0.1:6399", socket_connect_timeout=0.1)
    try:
        with pytest.raises(HTTPException) as error:
            await SaaS(saas.db, unavailable, cfg).throttle("test", "address")
        assert error.value.status_code == 503
    finally:
        await unavailable.aclose()
    for value in ["0", "-0.123456789012345678", "123456789012345678.1234567890123456"]:
        doc = document(
            tenant_id="test",
            environment="PAPER",
            record_ref=str(uuid4()),
            version_ref="v1",
            amount=decimal128(value),
        )
        await saas.db.ledger_events.insert_one(doc)
        stored = await saas.db.ledger_events.find_one({"_id": doc["_id"]})
        assert str(stored["amount"].to_decimal()) == value
    for invalid in [
        "NaN",
        "Infinity",
        "1e3",
        "1234567890123456789",
        "123456789012345678.123456789012345678",
    ]:
        with pytest.raises(ValueError):
            decimal128(invalid)
    with pytest.raises(ValueError):
        SaaSConfig(profile="PRODUCTION")
    await http.aclose()


@pytest.mark.asyncio
async def test_encrypted_local_delivery_and_unknown_obligations(tmp_path):
    cfg = SaaSConfig(keys={"mail": secrets.token_bytes(32)}, active_key="mail")
    mail = EncryptedLocalMail(cfg, tmp_path)
    raw = secrets.token_urlsafe(32)
    await mail.send("owner@example.test", "verify", raw, now() + timedelta(minutes=15))
    assert mail.read("owner@example.test", "verify") == raw
    assert raw not in next(tmp_path.glob("*.json")).read_text()
    wrong = EncryptedLocalMail(
        dataclasses.replace(cfg, keys={"mail": secrets.token_bytes(32)}), tmp_path
    )
    with pytest.raises(InvalidTag):
        wrong.read("owner@example.test", "verify")
    await mail.send("owner@example.test", "verify", raw, now() - timedelta(seconds=1))
    with pytest.raises(ValueError):
        mail.read("owner@example.test", "verify")
    assert not await FoundationObligations().safe_to_remove("tenant", "credential")
