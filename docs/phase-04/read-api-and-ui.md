# Read API and UI

Authenticated endpoints are `GET /api/v1/market/instruments`, `/candles`, and `/snapshot`. They validate uppercase symbols, allowed intervals, 200-day range and 1500-row maximum. Records are shared public infrastructure and contain no tenant secret. Sessions remain subject to Phase 3 expiry/revocation.

The chart explicitly switches between `Fixture` and `Live public feed`. Live failure shows disconnected/no stored data and never falls back to synthetic prices. Symbol, venue, interval and source are visible in status text. Current-candle records use open time as identity, preventing duplicate bars. Changing symbol/timeframe aborts the prior request. Private credential status stays separately `UNVERIFIED`; all execution controls remain disabled.

