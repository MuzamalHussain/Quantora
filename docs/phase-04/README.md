# Phase 4 — Binance public market ingestion

Status is governed by `evidence/gate-latest.json`. This phase is limited to public USDⓈ-M perpetual market data. It adds no credential use, private stream, order route, strategy, prediction or trading authority. `trading_enabled` remains false.

Rust owns provider normalization, bounded processing and order-book validity. FastAPI owns authenticated bounded reads. MongoDB owns durable normalized history; Redis may coordinate/cache but is never authoritative. React explicitly separates stored public data from the deterministic fixture.

