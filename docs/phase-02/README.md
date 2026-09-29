# QUANTORA Phase 2: architecture and runnable foundation

Current completion status is tracked in phase-02-report.md and scope-evidence.json, separately from the immutable Phase 1 baseline. This phase provides a local Rust core, FastAPI control API, React workspace, shared contracts and MongoDB/Redis infrastructure definitions. It provides no trading, tenant authentication, credential storage or model implementation.

Start with local-development.md. Run the final gate with `python scripts/verify_phase02.py` from the project root. It distinguishes static/unit checks, actual services, real dependency connectivity and browser evidence. Exit 2 means a mandatory check is blocked; it is not PASS. Evidence is stored under evidence/ and never upgrades the original Phase 1 acceptance scenarios.

Read architecture.md and service-and-data-boundaries.md for ownership; decision-resolutions.md for the actual D-01 through D-14 dispositions; contracts-and-versioning.md and configuration-and-secrets.md for input boundaries; verification-matrix.md and scope-evidence.json for evidence links. continuation-checkpoint.md is the recovery entry point after interruption.

The frontend displays deterministic synthetic candles, not market data. Mode badges are transport/configuration labels, not connected accounts. MongoDB remains the primary future application database; Redis is disposable. Phase 3 is not started.
