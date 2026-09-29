# Data quality and freshness

Per venue/symbol/channel records carry connection state, exchange time, UTC receive time, last success, latest valid event, epoch/sequence, coverage/gaps, validation failures and recovery attempts. Elapsed freshness uses a monotonic clock. States are `STARTING`, `SYNCING`, `LIVE`, `STALE`, `DEGRADED`, `DISCONNECTED`, `INVALID`.

Proposed development defaults are: mark/book/candle stream stale after 5 seconds beyond expected cadence; metadata stale after 15 minutes; OI stale after 5 minutes. These are operational defaults, not achieved SLOs. A quiet aggregate-trade channel remains connected when transport heartbeat and other channel evidence are healthy.

