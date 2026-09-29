# Instrument discovery

Eligibility requires `contractType=PERPETUAL`, quote and margin asset `USDT`, and status `TRADING`. Listed, eligible, selected, data-ready and future execution eligibility are separate states. `PRICE_FILTER.tickSize` and `LOT_SIZE.stepSize` are stored exactly; display precision is never substituted. Unknown filters/status values are retained but fail closed for eligibility. Missing instruments are versioned/staled, not deleted. Discovery failure preserves the last known universe and marks it stale.

