# Ingestion and storage

Rust is the sole market-processing owner. Provider payloads enter bounded queues and normalize to version 1 records. MongoDB v2 additive collections hold instrument heads/history, candles, OI/funding/mark observations, checkpoints, quality/recovery records and TTL diagnostic events. Natural keys make retries idempotent. Redis is optional coordination/cache only.

Candle requests require symbol, allowed interval, start/end and limit; the provider 200-day/1500-row bounds are enforced. Open time is the natural key. Forming bars remain provisional; closed observations are not silently replaced. A differing provider correction must create diagnostic/version evidence before propagation. Missing expected intervals are gaps; a no-trade conclusion requires provider evidence and is never invented. Full research replay and dataset splits remain Phase 5.

Diagnostic raw events use bounded TTL storage. Production retention remains unresolved under D-12. Mongo/Redis outage makes readiness truthful; it never silently redirects history to Redis.

