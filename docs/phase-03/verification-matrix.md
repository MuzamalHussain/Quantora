# Verification matrix

The current authority is evidence/gate-latest.json. `python scripts/verify_phase03.py` creates a timestamped run and exits 0 PASS, 1 FAIL or 2 BLOCKED. It invokes the complete Phase 2 gate, which includes Phase 1 hashes/regression, Rust, Python, contracts, frontend, Compose and real foundation runtime checks. It then uses a UUID-named Mongo database, ephemeral custody key and private encrypted test mailbox for Phase 3 browser evidence. Test-owned resources only are cleaned.

Phase 2's Python regression is deliberately scoped to `tests/test_foundation.py`; adding Phase 3 real-database tests must not turn an unavailable Phase 3 dependency into a false Phase 2 code regression. The Phase 3 runner separately executes `tests/test_saas.py` against real services and marks dependency unavailability BLOCKED.

| Area | Evidence | Required distinction |
|---|---|---|
| Authentication | Registration/login/logout/all/individual revoke; expiry/fixation/CSRF/origin/rate limit; token expiry/single-use/concurrency; password invalidation | Real Mongo/Redis; no plaintext/token assertions |
| Isolation/roles | Two tenants and admin; cross-ID GET/PUT/DELETE; list/query/summary/export; role/provider denial | Frontend visibility never substitutes server denial |
| Secrets | AES-GCM correct/wrong/missing key, tamper and AAD swap; lifecycle, unknown obligation denial, interrupted/resumed rotation; DB/response/log/audit/browser storage leak sentinels | Synthetic only; no provider connection |
| Data | Writable quantora-rs, transaction commit/rollback, concurrent idempotency, Decimal128, validators/indexes/duplicate preflight, migration first/repeat/failure/lock | Mock tests cannot satisfy this row |
| Redis outage | Atomic abuse counter and unreachable Redis rejection | Redis is transient; durable state remains Mongo |
| Backup/restore | Encrypted quiescent synthetic archive, new isolated DB, document/schema/index comparison and credential decryption | Not PITR or HA evidence |
| UI | Real registration/login/verification/settings/credential replace-disable-remove, session expiry/unauthorized view, 360/768/1440, fixture regression | No accessibility certification or fake status |
| Previous phases | verify_phase02.py | Phase 1 trading scenarios remain NOT_RUN |

The 2026-09-21 targeted run before Docker stopped recorded 8 real Phase 3 integration tests passing in 37.32s. A later independent run after mail/obligation changes recorded Ruff PASS, strict mypy PASS, frontend production build PASS and 37 tests (36 foundation plus encrypted-mail test) PASS in 8.88s. These are separate historical results; neither is relabeled as the final complete gate.

Mandatory final evidence remains BLOCKED while Docker Desktop cannot start its engine due to the inaccessible runtime socket `C:\Users\paren\AppData\Local\Docker\run\sailor-ingest.sock`. Its own crash report states it cannot rename that socket to `.stale`. The socket could not be renamed or removed even after Docker processes stopped. No factory reset, volume deletion or database reset was performed. The final gate must be rerun after Docker is repaired/rebooted.

Not Phase 3 evidence: external email deliverability, authenticated Binance behavior, live credentials/orders, production database authentication enforcement, HA/PITR, approved retention periods, load/availability targets, full accessibility or Phase 4 ingestion.

## Final repaired outcome — 2026-09-22T02:44:34Z

Overall PASS. Focused Phase 3 integration: 9 PASS/23.06s. Final gate: previous-phase gate PASS, Phase 3 real integration PASS (9/29.35s), real browser PASS (3/8.9s), documentation/registry PASS. Runtime recorded core, writable quantora-rs and Redis all UP; LIVE rejection, redaction and graceful shutdown PASS. Screenshots account-1440.png, account-768.png and account-360.png were visually reviewed with readable responsive content and no horizontal overflow. Historical BLOCKED/FAIL evidence remains timestamped and is not presented as PASS.
