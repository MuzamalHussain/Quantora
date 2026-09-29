# Binance endpoint and stream matrix

Verified against official Binance Developer documentation on 2026-09-22. REST base is `https://fapi.binance.com`; WebSocket base is `wss://fstream.binance.com`. All listed calls are public `NONE` security and use millisecond timestamps.

The current routed WebSocket endpoints are `/market/ws` for candles, mark price and aggregate trades, and `/public/ws` for incremental depth. Subscribe with lowercase stream names and wait for an acknowledgement before treating the subscription as live. An unrouted connection can upgrade while never delivering `/market` frames; this caused the original 15-second mark-price timeout. The repaired bounded test observed an acknowledged `btcusdt@markPrice@1s` subscription and an actual BTCUSDT data frame in `evidence/live-websocket.json`.

All rows below use public `NONE` security and **no API key**. Provider event and request timestamps are Unix milliseconds; numeric prices, quantities and rates arrive as decimal strings and remain strings in storage. `received_at_ms` is a separate local clock. The current [USDⓈ-M REST catalog](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data), [WebSocket routing](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/websocket-market-streams/Connect), and [book procedure](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/websocket-market-streams/How-to-manage-a-local-order-book-correctly) were checked again on 2026-09-22 UTC.

| Purpose | Endpoint/stream | Schema and bound or limitation |
|---|---|---|
| Exchange metadata | `GET /fapi/v1/exchangeInfo` | `symbols[]` with status, contract type and price/lot filters; weight 1; `rateLimits` currently shows 2400 REQUEST_WEIGHT per minute. Discovery is shared. |
| Candles | `GET /fapi/v1/klines` | 12-field rows with open/close times and OHLCV; limit 1500; 200-day request span; weight 1/2/5/10 by limit. The collector uses 1500 (weight 10). |
| Book snapshot | `GET /fapi/v1/depth` | `lastUpdateId`, `E`, `T`, bids/asks as `[price, quantity]`; 1000 levels cost weight 20 and are partial, not full depth. RPI orders are excluded. |
| Present OI | `GET /fapi/v1/openInterest` | `symbol`, `openInterest`, `time`; weight 1; point-in-time polling, not a WebSocket feed. |
| OI history | `GET /futures/data/openInterestHist` | `sumOpenInterest`, `sumOpenInterestValue`, `timestamp`; limit 500 and latest one month only; registered for bounded future backfill, not collected by the current point-in-time poll. |
| Mark/index/estimate | `GET /fapi/v1/premiumIndex` | mark, index, estimated funding and next funding time; weight 1 with symbol, 10 without. Bounded REST smoke only; continuous collector uses the routed mark stream. |
| Settled funding | `GET /fapi/v1/fundingRate` | `fundingRate`, `fundingTime`, optional mark and rate type; limit 1000; shares 500 requests/5 minutes/IP with `fundingInfo`. Collector polls two latest settled records at start and each 300-second cycle. |
| Candles | `/market/ws` subscribed to `<symbol>@kline_1m`, `_5m`, `_15m` | `k.t/T/o/h/l/c/v/x`; `x` distinguishes forming and closed bars. |
| Aggregate trades | `/market/ws` subscribed to `<symbol>@aggTrade` | `a/p/q/T`; aggregated executions, never labelled raw individual trades. |
| Mark price | `/market/ws` subscribed to `<symbol>@markPrice@1s` | `p/i/r/T/E`; funding `r` is an estimate, not settled history. |
| Best bid/ask | `<symbol>@bookTicker` | public best bid/ask stream is documented; the current collector derives top levels from synchronized depth instead of subscribing separately. |
| Incremental depth | `/public/ws` subscribed to `<symbol>@depth@100ms` | `U/u/pu`, absolute quantities, zero deletes; buffered during a 1000-level REST bridge. |

Official sources: [general information](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info), [REST market data](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data), [WebSocket streams](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/websocket-market-streams/Connect), [local book algorithm](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/websocket-market-streams/How-to-manage-a-local-order-book-correctly), and [live subscriptions](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/websocket-market-streams/Live-Subscribing-Unsubscribing-to-streams).

A connection lasts 24 hours, server ping frames arrive every 3 minutes, pong is required within 10 minutes, incoming messages are limited to 10/s, and a connection carries at most 1024 streams. Current terms do not establish unrestricted SaaS redistribution rights; production release requires legal/product resolution.

