# Dependency and version register

Existing installed versions and lockfiles were preserved during this continuation. Official documentation/release sources were inspected on 2026-09-15; this does not assert that every transitive package is the latest release. A future upgrade requires compatibility checks and deliberate lock regeneration.

| Layer | Selected versions | Reproducibility authority |
|---|---|---|
| Rust | Rust 1.98.1; Axum 0.8.9, Tokio 1.53.1, serde_json 1.0.151, jsonschema 0.33.0, UUID 1.26.1 | rust-toolchain.toml and services/trading-core/Cargo.lock; cargo --locked |
| Python | Python 3.12.10; FastAPI 0.141.1, Uvicorn 0.53.0, HTTPX 0.28.1, jsonschema 4.26.0, PyMongo 4.18.1, Redis client 8.1.0 | services/control-api/requirements.lock; includes exact transitive and verification packages |
| Browser | Node 24.18.0/npm 12.0.1; React/React DOM 19.3.0, TypeScript 7.0.2, Vite 8.3.0, Lightweight Charts 5.2.1, AJV 8.20.0 | Root package-lock.json, root/apps/web package.json |
| Verification | Playwright 1.63.0, Vitest 5.0.1, pytest 9.1.1, mypy 2.3.1, Ruff 0.16.7 | Same locks; local Microsoft Edge channel for browser checks |
| Local data services | Mongo official 8.0 image, Redis official 8 image | infra/images.lock.json records exact registry digest/source/date; compose.yaml uses digests |

Workspace-local Rust and Python tools already exist; no reinstall is needed to resume. Cargo manifest compatible ranges are resolved by the committed lock; npm dependencies are exact and transitive graph locked. Python uses the existing complete frozen environment. Image metadata retrieval proves registry identity, not that an image was pulled or executed. Docker is absent in this environment, so the container/config/connectivity gate remains blocked.

Rust jsonschema 0.33.0 is an existing compatible pin, not the newest package; draft-07 fixture validation is exercised in all three languages. No unsupported claim of latest-version parity is made. The production web build has a >500 kB chunk advisory, not a build failure; future code splitting should be based on measured deployment needs. Browser engine version is environment-owned and must be recorded/revalidated when changed; no browser binary was reinstalled.
