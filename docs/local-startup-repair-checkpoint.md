# Local development startup and account access — 2026-09-29

## Latest live-feed recovery — 2026-09-29

User asked whether deployment or Binance API secrets were needed for real candles. Neither is required for public USDⓈ-M market data. A bounded keyless request to official `/fapi/v1/time` and the exact `/fapi/v1/exchangeInfo` endpoint both returned HTTP 200, so the earlier HTTP 451 was not persistent at this check. `scripts/start-dev.ps1 -Action StartCollector` acquired the existing fenced lease and resumed bounded checkpoints. The application database gained 527 eligible instruments, BTCUSDT 1m/5m/15m candles from `BINANCE_WS`, and a valid synchronized book; later counts advanced from 62/12/4 to 124/24/8 with newer receive timestamps while the collector remained running. Core/API/web/MongoDB/Redis were also listening. The UI remains on labelled synthetic **Fixture** until the signed-in user selects **Live public feed**.

During observation, the first collector attempt stopped on a transient DNS `getaddrinfo failed` after storing genuine data. `scripts/phase04_collector.py` now retries transport errors with capped backoff only in continuous mode, retaining the lease/checkpoints and provider-weight budget; it still fails on HTTP 451 and provider bans. A focused fake-transport DNS recovery test and the existing rate-limit test both passed; Ruff passed. The restarted collector remained running through the later live-data check. `scripts/start-dev.ps1 -Action Status` now reports one status per role despite historical stopped collector PIDs. No private API key, secret or trading route was used.

Exact next action: in the already signed-in browser at `http://127.0.0.1:5173`, click **Live public feed**. It should show the stored BTCUSDT public candles and source/freshness status. If the provider becomes unavailable again, keep the stale/disconnected state honest and inspect `scripts/start-dev.ps1 -Action Status`; do not substitute fixture data or add private credentials.

## 2026-09-29 user screenshot follow-up

The signed-in screenshot shows the **Fixture** button selected and a labelled synthetic `SYNTH/USDT` chart. This is the deliberate deterministic demonstration, not Binance data. The `Live public feed` button requests authenticated stored public candles and never substitutes the fixture on failure. The local collector is still stopped after an actual Binance REST HTTP 451 at `exchangeInfo`; core/API/web/MongoDB/Redis remain running. No private key can repair a public-provider 451. The account page copy now explicitly explains that its API key/secret form only stores future private-account credentials and neither enables trading nor supplies public candles. `npm run build` passed after the copy change. The user's screenshot shows the requested email has since been registered as a signed-in, unverified tenant owner; its password remains unknown to the assistant. Exact next action for real public candles remains lawful public REST availability, followed by one `scripts/start-dev.ps1 -Action StartCollector` retry and authenticated live-feed inspection. Do not ask the user to enter Binance credentials for this step.

## Confirmed diagnosis and repair

`npm run dev` launches only Vite. Vite correctly proxies `/api` to `127.0.0.1:8000`, but no API or Rust core process was listening. Existing MongoDB (27117) and Redis (6381) containers were healthy. The default application DB `quantora_app` had no users or encrypted credentials and had a Phase 4 `v2-market` marker but no Phase 3 `v1` marker. The v1 migration refused its unvalidated `migrations` collection. `quantora_api/data.py` now validates every existing marker before attaching the exact v1 validator, preserving the v2 marker and all records. A focused real-Mongo regression passed and the application v1 migration completed. No collection, volume, key or account was reset.

The process environment had no custody key or development mailbox configured. With the app DB confirmed to contain no encrypted credentials, `scripts/start-dev.ps1 -Action InitializeSecrets` created a new 32-byte local key protected by Windows DPAPI for the current user in ignored `.cache/dev-custody-key.dpapi`. This is the first local app key, not a replacement. `scripts/local_key_guard.py` prevents this operation if encrypted records/mail exist or the database is unavailable. Preserve and securely back up this key file before storing credentials; losing it makes encrypted data unrecoverable. The launcher loads it into child-process environment without printing it and uses ignored `.cache/local-mail` for development-only encrypted mail.

## Repeatable workflow

From the project root, with the existing MongoDB and Redis containers running, use `npm run dev` (or the equivalent direct launcher command):

```powershell
powershell -NoProfile -File scripts\start-dev.ps1
```

The root `npm run dev` now uses this launcher and safely reports already-running services. `npm run dev:web` starts only Vite for deliberate frontend-only work and requires port 5173 to be free; it does not start the API or Rust core.

The one-time `-Action InitializeSecrets` step has already been completed for this workspace. If moving to another Windows user or machine, restore the original protected key through a secure key-transfer process; do not initialize a new key over existing encrypted data. On a genuinely empty new local database, `-Action InitializeSecrets` is the explicit first-run step.

Open `http://127.0.0.1:5173`. This starts the built Rust core, FastAPI, Vite and one bounded-epoch public BTCUSDT collector, checks service readiness, records owned PIDs and sanitized logs under ignored `.cache`, and does not duplicate already-running services. `-Action Status` checks listeners and owned processes; `-Action Stop` stops only launcher-owned children. `-Action StartCollector` makes one explicit public-feed retry after an external provider restriction is resolved. Test runners are separate: they own temporary servers and shut them down after verification.

## Account and administrator

The requested `mh5071324@gmail.com` account is **absent** in `quantora_app`; no password was set or exposed. At the local URL, open Account, choose Create account, enter this email and a password locally (12–128 characters), then sign in. Registration is generic by design and does not reveal whether an email is already registered. For local verification, request a verification delivery in Account, then in a local PowerShell terminal run:

```powershell
powershell -NoProfile -File scripts\start-dev.ps1 -Action ReadMail
```

Enter the email and purpose `verify` interactively, then paste the token only into the local UI. This is encrypted development mail; **no external email is sent**. Do not put passwords, tokens or keys in chat, source control or command arguments.

There is no default PLATFORM_ADMIN. The existing interactive implementation is `../../.venv/Scripts/python.exe -m quantora_api.manage bootstrap-admin` from `services/control-api`; the key-loading wrapper is:

```powershell
powershell -NoProfile -File scripts\start-dev.ps1 -Action BootstrapAdmin
```

It prompts locally for a separate admin email and confirmed password via `getpass`, after migration. An existing email fails without role or password changes. The same identity cannot simultaneously be tenant owner and platform admin in this model; choose a distinct administrator address deliberately. No account was promoted. Admin has no tenant impersonation or plaintext tenant-credential HTTP access.

## Actual checks and current limit

Focused migration tests: 2 passed. Ruff on changed Python passed; mypy on the changed persistence module passed; the read-only key-initialization guard passed. The isolated real-service browser run: 4 passed, including registration, login, verification, settings, custody and market fixture/stored-state behavior. Core/API readiness and dependency checks passed; `GET /health/ready`, `/api/v1/foundation/status` and `/auth/csrf` returned 200. Anonymous `/auth/me` and `/market/instruments` returned expected 401, including through Vite's proxy; this is not service unavailability. The proxied foundation status reports READY, core/MongoDB/Redis UP, and `trading_enabled=false`. The user-facing core/API/web services were restored after the isolated test and remain running. Reissuing the startup command detected them and started no duplicate.

At the original startup check, the public collector stopped on Binance's actual HTTP **451** response from `GET /fapi/v1/exchangeInfo`; the log preserves that event. That historical restriction was not bypassed. The later live-feed recovery above supersedes its then-current blocker and empty-database assessment.
