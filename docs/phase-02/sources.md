# Phase 2 official sources

Observed 2026-09-15 in the earlier continuation. These dates are preserved; local verification on 2026-09-16 does not redate source retrieval. Sources establish APIs/licensing/topology choices, not application correctness or production acceptance.

| Source | Evidence used / limitation |
|---|---|
| https://tradingview.github.io/lightweight-charts/docs | Financial series, TypeScript and required attribution |
| https://github.com/tradingview/lightweight-charts/releases/tag/v5.2.1 | Installed release identity |
| https://raw.githubusercontent.com/tradingview/lightweight-charts/v5.2.1/NOTICE | Exact distribution notice; copied to public notices and UI |
| https://github.com/tradingview/lightweight-charts/blob/master/LICENSE | Apache-2.0; installed full license copied into public assets |
| https://tradingview.github.io/lightweight-charts/docs/plugins/intro | Extensibility, not implemented complete drawing tools |
| https://github.com/apache/echarts | Accessible alternative, Apache-2.0 and general chart scope; no prototype benchmark |
| https://echarts.apache.org/handbook/en/basics/download/ | Alternative install route |
| https://react.dev/versions | React release documentation |
| https://vite.dev/guide/ | Vite toolchain integration |
| https://nodejs.org/en/about/previous-releases | Node release/support line selection |
| https://fastapi.tiangolo.com/release-notes/ | API dependency release review |
| https://fastapi.tiangolo.com/advanced/events/ | Lifespan startup/shutdown |
| https://rust-lang.org/tools/install/ | Official Rust toolchain installation source |
| https://docs.rs/axum/latest/axum/ | Rust HTTP framework |
| https://docs.rs/jsonschema/0.33.0/jsonschema/ | Existing validator pin/API |
| https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html | Locked dependency graph |
| https://json-schema.org/draft-07 | Canonical schema dialect |
| https://www.mongodb.com/docs/manual/replication/ | Replica topology; single member is not high availability |
| https://www.mongodb.com/docs/manual/release-notes/8.0/ | MongoDB selected server line |
| https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-targets/ | Direct connection for local replica set exposure |
| https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/docker/ | Local Redis container guidance |
| https://hub.docker.com/v2/repositories/library/mongo/tags/8.0 | Exact digest retained in infra/images.lock.json |
| https://hub.docker.com/v2/repositories/library/redis/tags/8 | Exact digest retained in infra/images.lock.json |

Phase 1 source records remain historical. No exchange endpoint, regional availability, signing workflow or real Binance compatibility was newly verified in Phase 2. D-10 explicitly blocks reliance on those assumptions until integration verification.
