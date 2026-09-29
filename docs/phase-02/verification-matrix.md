# Verification matrix

Current machine evidence: evidence/gate-latest.json (final gate) and evidence/runtime-latest.json (real processes). Timestamped gate directories retain command logs. Prior September 15 runtime evidence is archived in evidence/prior-20260915. Earlier counts are historical, not newly executed results.

| Gate key | Class and command | Acceptance / scope |
|---|---|---|
| baseline_hashes | Static SHA-256 comparison against baseline-hashes.json | All 23 baseline files unchanged |
| phase01 | Structural: python scripts/validate_phase01.py | Original registry/document relationships; not application tests |
| phase01_regression | Structural: python scripts/test_validate_phase01.py | Original corruption regression checks |
| rust_fmt | Static: cargo fmt --check | Formatting |
| rust_build | Build: cargo build --locked | Actual executable |
| rust_clippy | Static: cargo clippy --locked --all-targets -- -D warnings | Rust lint |
| rust_tests | Unit: cargo test --locked | Shared fixtures, mode/redaction/routes/body and queue limits |
| python_lint | Static: python -m ruff check . | Configured API lint |
| python_types | Static: python -m mypy | Strict API source types |
| python_tests | Unit: python -m pytest -q | Shared fixtures, mode/URL/error/redaction/limits/CORS, mocked ready/unready and lifespan; mocks are not real integration |
| generated_contracts | Static: node scripts/generate-contracts.mjs --check | Generated TS remains aligned to schema |
| web_build | Type/build: npm run build --workspace apps/web | TypeScript and production bundle |
| web_tests | Unit: npm run test --workspace apps/web | Shared fixtures, nonfinite rejection, aggregation |
| compose_config | Static: docker compose -f infra/compose.yaml config --quiet | Compose interpretation; BLOCKED if Docker absent |
| runtime | Real: python scripts/verify_runtime.py | Actual Rust/API startup, HTTP ping, mode rejection, redaction, graceful shutdown; real Mongo primary/Redis PING required for PASS |
| browser (within runtime) | Real Edge UI + separate fault injection | Candles/aggregation/resize/keyboard/labels/empty states/status; unreachable response uses explicit route abort |
| documentation | Structural/manual | Required files, valid requirement IDs, artifact references, declared future-only boundaries; semantic review recorded in report |

The final gate records each command's exit, time, log and status. Exit 0 is PASS; exit 1 is FAIL; exit 2 is BLOCKED. Missing Mongo/Redis availability cannot be replaced by unit mocks. Runtime result explicitly records each dependency. A BLOCKED overall result does not erase passing independent checks.

Not run in this phase: exchange connectivity/orders, authentication/security integration, trading acceptance, failover/backup restore, throughput/soak/latency SLOs, full accessibility certification, production deployment or CI. All 73 original future acceptance scenarios remain NOT_RUN. Browser screenshots require visual review in addition to automated assertions.

## Final recorded outcome — 2026-09-15T22:20:41Z

Overall BLOCKED. Baseline, Rust, Python, frontend, generated contracts and document-reference checks PASS. Counts: Rust 4, Python 36, frontend 24, browser 2. Real startup/API-core/redaction/LIVE rejection/shutdown PASS. Compose and real available Mongo/Redis are BLOCKED. See phase-02-report.md and evidence/20260915T221815Z/gate.json for exact commands/results. Three screenshots visually reviewed; no complete accessibility or trading acceptance claim.


## Phase 3 baseline resolution — 2026-09-21T09:01:01Z

Current Phase 2 status: PASS. Fresh verify_phase02.py completed all gates, including Compose and real MongoDB/Redis readiness. Earlier BLOCKED entries remain historical. Evidence: evidence/20260921T090018Z/gate.json. Phase 3 is now authorized by the subsequent user prompt.
