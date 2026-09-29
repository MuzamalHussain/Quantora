"""Bounded, keyless Binance USDⓈ-M public smoke. Never sends mutation requests."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

REST = "https://fapi.binance.com"
SYMBOL = "BTCUSDT"


async def rest(http: httpx.AsyncClient, path: str, params: dict[str, object] | None = None):
    response = await http.get(REST + path, params=params)
    response.raise_for_status()
    return response.json(), {k.lower(): v for k, v in response.headers.items() if k.lower().startswith("x-mbx-used-weight")}


async def main() -> int:
    async with httpx.AsyncClient(timeout=8, follow_redirects=False) as http:
        exchange, exchange_headers = await rest(http, "/fapi/v1/exchangeInfo")
        eligible = [s for s in exchange["symbols"] if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT" and s.get("marginAsset") == "USDT" and s.get("status") == "TRADING"]
        klines, kh = await rest(http, "/fapi/v1/klines", {"symbol": SYMBOL, "interval": "1m", "limit": 3})
        depth, dh = await rest(http, "/fapi/v1/depth", {"symbol": SYMBOL, "limit": 100})
        oi, oh = await rest(http, "/fapi/v1/openInterest", {"symbol": SYMBOL})
        premium, ph = await rest(http, "/fapi/v1/premiumIndex", {"symbol": SYMBOL})
        funding, fh = await rest(http, "/fapi/v1/fundingRate", {"symbol": SYMBOL, "limit": 2})
    evidence = {
        "schema_version": 1, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"rest": REST},
        "credentials_used": False, "mutation_requests": 0, "symbol": SYMBOL,
        "discovery": {"eligible_count": len(eligible), "sample": [s["symbol"] for s in eligible[:5]], "headers": exchange_headers},
        "candles": {"count": len(klines), "first_open_time_ms": klines[0][0], "headers": kh},
        "depth": {"last_update_id": depth["lastUpdateId"], "bid_levels": len(depth["bids"]), "ask_levels": len(depth["asks"]), "headers": dh},
        "open_interest": {"source_time_ms": oi["time"], "present": bool(oi.get("openInterest")), "headers": oh},
        "premium": {"source_time_ms": premium["time"], "mark_present": bool(premium.get("markPrice")), "index_present": bool(premium.get("indexPrice")), "headers": ph},
        "funding": {"settled_records": len(funding), "headers": fh},
    }
    target = Path(os.getenv("QUANTORA_PHASE04_LIVE_EVIDENCE", "docs/phase-04/evidence/live-smoke.json"))
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "evidence": str(target), "eligible": len(eligible)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
