# Verification matrix

Latest strengthened gate: `evidence/20260928T130231Z/gate.json` — **PASS**. Historical runs remain preserved; dates below identify when evidence was actually produced.

| Gate | Required evidence | Actual result |
|---|---|---|
| Previous phases | fresh Phase 3 runner including Phase 1/2 baseline | PASS, 2026-09-28 gate |
| Rust processing | format, Clippy, tests, processor build | PASS, 2026-09-28 gate |
| Python and web quality | Ruff, strict mypy, TypeScript/Vite build | PASS, 2026-09-28 gate |
| Real persistence/security | MongoDB/Redis integration, migration, lease takeover/fencing, API/session tests | PASS, 15 tests, 2026-09-28 gate |
| Public REST | keyless exchange discovery, candles, depth, OI, premium/funding | PASS, `evidence/live-smoke.json` (2026-09-22), unchanged smoke implementation; public exchangeInfo independently HTTP 200 on 2026-09-28 |
| Public WebSocket | routed subscription acknowledgement and actual market frame | PASS, `evidence/live-websocket.json` (2026-09-22) and fresh collector stream counts on 2026-09-28 |
| Shared collector | bounded real BTCUSDT stream, Rust normalization/book, REST polls, fenced writes | PASS, `evidence/20260928T130231Z/collector.log` and `collector-storage.json` |
| Checkpoints/restart | durable 1m/5m/15m checkpoints and ownership fence advance | PASS, storage assertions; focused resumed collector fence 7, browser second collector fence 2 |
| Live API/chart | newer WebSocket candle visible while open chart remains on screen | PASS, 4 browser tests and `evidence/20260928T130231Z/live-chart.json` |
| Fault/freshness | invalid book/queue/reconnect/rate tests; controlled browser disconnect | PASS, integration and browser; terminal stream state `DISCONNECTED` |
| Documentation | required files and registry | PASS for file presence in gate; semantic reconciliation completed after gate |

The final gate's live collector and browser checks are fresh. The preserved REST/WebSocket smoke files are earlier real-provider observations, not newly executed smoke commands. Bounded functional acceptance does not certify production load, long-duration operation, redistribution rights or retention policy.
