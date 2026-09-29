"""Shared, read-only market-data persistence and bounded authenticated API."""

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from .data import DB, Doc
from .saas_routes import Current, service

MARKET_SCHEMA_VERSION = 1
SYMBOL = r"^[A-Z0-9]{5,24}$"
INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"}

COLLECTIONS: dict[str, dict[str, Any]] = {
    "market_instruments": {"keys": [("venue", 1), ("symbol", 1)], "unique": True},
    "market_instrument_versions": {"keys": [("venue", 1), ("symbol", 1), ("effective_at_ms", 1)], "unique": True},
    "market_candles": {"keys": [("venue", 1), ("symbol", 1), ("interval", 1), ("open_time_ms", 1)], "unique": True},
    "market_observations": {"keys": [("venue", 1), ("symbol", 1), ("kind", 1), ("source_time_ms", 1)], "unique": True},
    "market_checkpoints": {"keys": [("channel", 1), ("symbol", 1), ("interval", 1)], "unique": True},
    "market_quality": {"keys": [("venue", 1), ("symbol", 1), ("channel", 1), ("recorded_at", -1)], "unique": False},
    "market_raw_events": {"keys": [("expire_at", 1)], "unique": False, "ttl": 0},
}
MIGRATION_CHECKSUM = hashlib.sha256(json.dumps(COLLECTIONS, sort_keys=True).encode()).hexdigest()


async def migrate_market(db: DB) -> None:
    """Additive v2 migration. It never edits the already-applied Phase 3 v1."""
    old = await db.migrations.find_one({"_id": "v2-market"})
    if old:
        if old.get("checksum") != MIGRATION_CHECKSUM:
            raise RuntimeError("Phase 4 migration checksum changed")
        return
    for name, spec in COLLECTIONS.items():
        if name not in await db.list_collection_names():
            await db.create_collection(name)
        options: dict[str, Any] = {"unique": spec["unique"], "name": "phase04_natural_key"}
        if "ttl" in spec:
            options["expireAfterSeconds"] = spec["ttl"]
        try:
            await db[name].create_index(spec["keys"], **options)
        except DuplicateKeyError as exc:
            raise RuntimeError(f"Conflicting Phase 4 records in {name}") from exc
    await db.migrations.insert_one({
        "_id": "v2-market", "schema_version": 1, "created_at": datetime.now(UTC),
        "version": 2, "checksum": MIGRATION_CHECKSUM,
    })


async def market_ready(request: Request) -> DB:
    saas = await service(request)
    await migrate_market(saas.db)
    return saas.db


MarketDB = Annotated[DB, Depends(market_ready)]
router = APIRouter(prefix="/api/v1/market", tags=["market"])


def validate_symbol(symbol: str) -> str:
    if not __import__("re").fullmatch(SYMBOL, symbol):
        raise HTTPException(400)
    return symbol


@router.get("/instruments")
async def instruments(_: Current, db: MarketDB, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0, le=5000)) -> Doc:
    values = await db.market_instruments.find({}, {"_id": 0}).sort("symbol", ASCENDING).skip(offset).to_list(limit)
    return {"schema_version": MARKET_SCHEMA_VERSION, "venue": "BINANCE_USDM", "items": values, "next_offset":offset+len(values) if len(values)==limit else None}


@router.get("/candles")
async def candles(_: Current, db: MarketDB, symbol: str, interval: str, start_ms: int, end_ms: int, limit: int = Query(500, ge=1, le=1500)) -> Doc:
    symbol = validate_symbol(symbol)
    if interval not in INTERVALS or start_ms < 0 or end_ms <= start_ms or end_ms - start_ms > 200 * 86_400_000:
        raise HTTPException(400)
    query = {"venue": "BINANCE_USDM", "symbol": symbol, "interval": interval, "open_time_ms": {"$gte": start_ms, "$lt": end_ms}}
    items = await db.market_candles.find(query, {"_id": 0}).sort("open_time_ms", ASCENDING).to_list(limit)
    return {"schema_version": MARKET_SCHEMA_VERSION, "symbol": symbol, "interval": interval, "items": items}


@router.get("/snapshot")
async def snapshot(_: Current, db: MarketDB, symbol: str) -> Doc:
    symbol = validate_symbol(symbol)
    observations = await db.market_observations.find({"venue": "BINANCE_USDM", "symbol": symbol}, {"_id": 0}).sort("source_time_ms", DESCENDING).to_list(20)
    quality = await db.market_quality.find({"venue": "BINANCE_USDM", "symbol": symbol}, {"_id": 0}).sort("recorded_at", DESCENDING).to_list(20)
    feed=next((item for item in quality if item.get("channel")=="STREAM"),None)
    age=max(0,int(datetime.now(UTC).timestamp()*1000)-feed["received_at_ms"]) if feed and feed.get("received_at_ms") else None
    feed_state=feed.get("state","DISCONNECTED") if feed else "DISCONNECTED"
    if feed_state=="LIVE" and (age is None or age>5000): feed_state="STALE"
    book=next((item for item in observations if item.get("kind")=="BOOK"),None)
    book_age=max(0,int(datetime.now(UTC).timestamp()*1000)-book["received_at_ms"]) if book and book.get("received_at_ms") else None
    book_current=bool(book and book.get("valid") and feed_state=="LIVE" and book_age is not None and book_age<=5000)
    return {"schema_version": MARKET_SCHEMA_VERSION, "symbol": symbol, "observations": observations, "quality": quality, "public_feed_state":feed_state, "feed_age_ms":age, "book_current":book_current,"book_age_ms":book_age,"trading_enabled": False}


@router.get("/stream")
async def stream(request: Request, identity: Current, db: MarketDB, symbol: str) -> StreamingResponse:
    """Bounded same-origin SSE view of normalized shared state; no provider secret crosses it."""
    symbol = validate_symbol(symbol)
    _, session = identity
    saas = await service(request)

    async def events() -> AsyncIterator[str]:
        last_id: str | None = None
        for _ in range(300):  # five-minute connection cap; clients reconnect explicitly
            if await request.is_disconnected():
                return
            try:
                _, current_session = await saas.context(request.cookies.get(saas.config.cookie))
            except HTTPException:
                return
            if current_session["_id"] != session["_id"]:
                return
            item = await db.market_observations.find_one(
                {"venue": "BINANCE_USDM", "symbol": symbol}, {"_id": 0}, sort=[("source_time_ms", DESCENDING)]
            )
            event_id = json.dumps(item, default=str, sort_keys=True) if item else ""
            if event_id != last_id:
                last_id = event_id
                yield "event: market\ndata: " + json.dumps({"symbol": symbol, "observation": item, "trading_enabled": False}, default=str) + "\n\n"
            else:
                yield ": keepalive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})
