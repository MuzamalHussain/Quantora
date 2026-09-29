# Configuration and secrets

Bootstrap process configuration is separate from future dashboard provider credentials. `.env.example` contains only safe local examples; neither service implicitly reads .env. Set process variables explicitly. API configuration accepts local HTTP, MongoDB and Redis addresses with explicit ports; rejects remote hosts, embedded credentials, fragments and core/origin path/query injection. Core bind must be a nonzero loopback socket. These restrictions intentionally limit this unauthenticated foundation to local development.

| Variable | Default / behavior |
|---|---|
| QUANTORA_MODE | PAPER; PAPER/REPLAY/SHADOW/TESTNET are labels only; LIVE and unknown/case-mismatched values fail startup |
| QUANTORA_CORE_BIND | 127.0.0.1:8101, Rust only |
| QUANTORA_CORE_URL | http://127.0.0.1:8101 |
| QUANTORA_MONGO_URL | mongodb://127.0.0.1:27117/?directConnection=true&replicaSet=quantora-rs |
| QUANTORA_REDIS_URL | redis://127.0.0.1:6381/0 |
| QUANTORA_CORS_ORIGIN | http://127.0.0.1:5173; exact allowlist, no credentials |

API binds 127.0.0.1:8000. Development/preview Vite proxies /api from ports 5173/4173 to this address. Browser preview is same-origin through that proxy; it does not require a wildcard CORS change. Standard CORS preflight responses follow framework behavior; application errors use canonical ERROR envelopes. No API keys, stored secrets or environment-only Binance integration exist.

LIVE cannot be enabled by an environment toggle because validation rejects it and there is no exchange/order adapter. Other mode labels also have trading_enabled=false. Startup failure prints only a fixed event, never the rejected value. Runtime logs allow only internal event labels, UUID, status, UTC time and monotonic duration. Query strings, request bodies, Authorization headers, URLs, connection strings and exception messages are excluded. Test sentinels are synthetic only.

The Phase 3 custody design is contracts/secret-manager-interface.md. It keeps root encryption material outside encrypted-credential storage and requires authenticated tenant/environment operations. This is design evidence, not a completed encryption/security subsystem.
