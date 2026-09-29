# Phase 4 report

**Current status: PASS.** The strengthened final gate `evidence/20260928T130231Z/gate.json` completed on 2026-09-28 at 13:06:49 UTC. Historical FAIL/BLOCKED runs remain preserved.

## Implemented scope

The runnable shared public collector (`scripts/phase04_collector.py`) owns a fenced MongoDB lease. It dynamically discovers eligible Binance USDⓈ-M perpetuals, resumes bounded 1m/5m/15m backfill from durable checkpoints, revisits forming bars, records gaps/corrections, and polls open interest and settled funding. Rust `market_processor` normalizes provider events and processes snapshot-plus-delta order books. Routed `/market/ws` and `/public/ws` subscriptions carry candle, mark-price, aggregate-trade, and depth events through bounded queues into fenced MongoDB writes. Each reconnect takes a fresh book snapshot; invalid sequences and crossed or empty books suppress current-book publication. The collector has bounded cycles and continuous operation, lease renewal, persisted 429/418 cooldowns, provider-weight accounting, and explicit disconnected/freshness state. The gate verifies bounded function, not production-scale capacity or long-duration operation.

The additive `v2-market` migration preserves Phase 3 v1 data and keys. Authenticated API endpoints provide bounded instrument, candle, snapshot and SSE reads with session revalidation. The React workspace separates fixture from stored public data, loads the eligible universe, offers 1m/5m/15m charts, refreshes live candles, and shows public-feed source/freshness separately from private credential verification. Trading remains disabled. No private credential or account request was used and no order was sent.

## WebSocket diagnosis and repair

The original no-frame attempts used an unrouted USDⓈ-M WebSocket URL. Binance's current routing requires `/market/ws` for mark price, candles and trades, while depth uses `/public/ws`. The repaired keyless smoke `evidence/live-websocket.json` records a subscription acknowledgement and actual BTCUSDT `markPriceUpdate` frame. The collector's routed streams then delivered real frames in the final gate. A later 2026-09-22 gate failed independently at TLS connection to public REST `exchangeInfo`; direct REST and the focused resumed collector succeeded on 2026-09-28. That transient timeout is no longer an active blocker. No timeout increase, fixture substitution or restriction bypass was used.

## Actual verification

The 2026-09-28 final gate recorded previous Phase 1–3 gate PASS; Rust format, Clippy, unit tests and processor build PASS; Ruff PASS; strict mypy PASS; web build PASS; real MongoDB/Redis integration **15 passed**; public REST evidence PASS; public WebSocket frame evidence PASS; fresh live collector PASS; real storage/book/checkpoint assertions PASS; browser **4 passed**; open-chart live update PASS; documentation file check PASS. Its first collector received 138 depth, 102 kline, 14 mark and 162 trade events, plus 1 open-interest and 2 settled-funding polls. It stored 527 eligible instruments, 1m/5m/15m BTCUSDT candles, a valid order book, bounded raw diagnostics and all three backfill checkpoints. A second fenced collector advanced to fence 2 while the browser chart was open. `evidence/20260928T130231Z/live-chart.json` records a visible BTCUSDT 1m chart with a newer `BINANCE_WS` receive timestamp.

The browser checked timeframe switching, controlled disconnection without synthetic fallback, disabled execution, and responsive 1440/768/360 screenshots. Current `evidence/market-*.png` screenshots show the post-fault disconnected state; the live update is evidenced by the browser assertion and timestamped JSON, not those screenshots. A focused resumed collector run against the existing isolated test database passed before the gate (fence 7, 76 resumed backfill rows, 138 depth/111 kline/14 mark/154 trade events). No user database, key, credential, volume or completed backfill was reset.

## Remaining limits and decisions

Production load, long-duration operation, venue redistribution rights and production retention policy D-12 remain release/operations decisions, not failures of the bounded Phase 4 functional gate. No mandatory Phase 4 blocker remains. Phase 5 has not started.
