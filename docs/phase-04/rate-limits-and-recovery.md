# Rate limits and recovery

One shared IP budget accounts for discovery/broad streams separately from per-symbol depth and OI. Response `X-MBX-USED-WEIGHT-*` headers update observed use. HTTP 429 honors `Retry-After` and stops new work; 418 enters a ban state with no aggressive retry. Transient 5xx/timeouts use bounded exponential backoff with jitter. Fault tests simulate responses locally.

Connections rotate before the documented 24-hour expiry, answer ping frames, bound subscription messages below 10/s, limit each socket below 1024 streams and cap detailed symbols by configuration. Cancellation closes queues/tasks. Collector duplicate-instance protection uses a fenced Mongo lease; an uncertain/expired lease inhibits publication until reacquired. No capacity beyond the tested bounded sample is claimed.

