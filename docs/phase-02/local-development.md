# Local development

For the current Phase 3/4 application with accounts and public market data, use `docs/local-startup-repair-checkpoint.md` and `scripts/start-dev.ps1`. The commands below document the original Phase 2 foundation startup and gate.

Run commands from the repository root unless a directory change is shown. Windows evidence uses Python 3.12.10, Node 24.18.0 and Rust 1.98.1 with Visual Studio Build Tools. Dependencies are already installed in this workspace; do not reinstall to resume. On a fresh checkout, create a Python 3.12 virtual environment, install `services/control-api/requirements.lock`, run `npm ci`, and install the pinned Rust toolchain. Cargo.lock must remain committed with the service. Dependencies are pinned; do not use update commands as a routine startup step.

```powershell
# Existing workspace Rust toolchain; use ordinary cargo if installed globally elsewhere.
. .\scripts\rust-env.ps1
cargo build --manifest-path services/trading-core/Cargo.toml --locked
# Terminal 1:
cargo run --manifest-path services/trading-core/Cargo.toml --locked
# Terminal 2:
Set-Location services/control-api
..\..\.venv\Scripts\python.exe -m quantora_api
# Terminal 3, from root:
npm.cmd run dev
```

The chart works without infrastructure; actual dependency status will say DOWN/NOT_READY. Open http://127.0.0.1:5173 locally. For production build feasibility, `npm.cmd run build` then `npm.cmd run preview --workspace apps/web` serves the built files on loopback port 4173; this is not a production deployment.

## MongoDB/Redis infrastructure

Docker with Linux containers and Compose is required for the supplied infrastructure. It is absent on the inspected host; WSL is also not installed. No global runtime installation or unrelated service change was performed. Once Docker is available:

```powershell
docker compose -f infra/compose.yaml config --quiet
docker compose -f infra/compose.yaml up -d
docker compose -f infra/compose.yaml logs mongo-init
docker compose -f infra/compose.yaml exec mongodb mongosh --quiet --eval 'db.hello()'
docker compose -f infra/compose.yaml exec redis redis-cli PING
```

The init job is idempotent only for the expected quantora-rs identity; it never reconfigures another set. MongoDB binds inside the container with host exposure restricted to 127.0.0.1:27117 and persistent volume quantora_phase02_mongo_data. Redis is limited to 64mb with disposable, nonpersistent cache semantics on 127.0.0.1:6381. Mongo's healthcheck covers process availability; the API separately requires replica primary readiness. The host driver uses directConnection to access the single published replica member, whose internal hostname is mongodb:27017. This local topology is not production HA.

Normal shutdown: stop owned API/core terminals using Ctrl+C, then `docker compose -f infra/compose.yaml down`. This preserves Mongo data. Volume removal is destructive and is neither part of startup nor performed by verification. No reset command is supplied or executed; do not remove unrelated databases/volumes.

## Verification

```powershell
python scripts/verify_phase02.py
```

The gate builds/tests without reinstalling dependencies, checks Phase 1 hashes, starts owned service children only on free ports, runs actual health/ping and browser checks, then requests graceful shutdown. Existing listeners cause BLOCKED instead of replacement. Browser tests use installed Microsoft Edge via Playwright; set QUANTORA_BROWSER_CHANNEL=chromium on a host with the matching Playwright browser installed. The gate does not silently start Docker or create/reset databases. A required unavailable dependency means exit 2/BLOCKED.
