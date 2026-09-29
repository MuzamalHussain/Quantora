# Service and data boundaries

| Component | Owns now | Does not own now |
|---|---|---|
| Browser | Chart fixtures, selected aggregation and honest status presentation | API secrets, authenticated tenant identity, trade submission |
| Control API | Bootstrap validation, health aggregation, error/correlation/log boundary, schema-checked ping forwarding | Authentication, memberships, balances, stored credentials, strategy |
| Rust core | Health, bounded ping worker, request limits, mode validation, graceful stop | Orders, exchange adapters, ledger, live routing |
| MongoDB local replica set | Empty isolated persistent infrastructure, when started | Any claimed financial business record or tested production failover |
| Redis | Disposable local server, when started | Durable/authoritative financial state |
| Research/object storage | Contract documentation only | Running service, model training, production model |

All foundation services bind loopback. They have no authentication and must not be exposed publicly. CORS is a browser policy, not authorization. Forwarded HTTP requests use a configured local base URL, no user-supplied destination, no environment proxy and no redirects. The response must conform to the canonical schema and identify the compatible foundation core.

Future private position-intent, execution and credential-metadata envelopes require tenant_id and account_id; those fields are identifiers, not proof of authorization. Phase 3 must derive tenant context from authenticated identity and enforce scope at every data/stream/job boundary. Shared market/forecast envelopes can be tenant-independent. No fake account-management route is provided in Phase 2.

## Future financial dispatch boundary (design only)

Before remote dispatch, persist immutable intent ID, unique client-order ID, account/environment identity, config/risk version, reservation and fence token in MongoDB with majority journaled acknowledgement. Commit of that transaction does not commit an exchange order. The single fenced account writer checks current ownership before dispatch. Pending/unknown orders retain reserved risk until conclusive reconciliation. Duplicate fills use venue/account/environment/transaction identity and append corrections, rather than reapplying effects. An outbox/reconciler must recover intent-versus-exchange uncertainty after crashes; blind retry is prohibited. No such ledger or writer is implemented here.

Future index design: unique (tenant, account, environment, intent_id) and client_order_id constraints prevent duplicate dispatch identities; unique (venue, account, environment, exchange_fill_id) prevents duplicate fill effects. Account ownership is unique per account/environment with a monotonically increasing fence; outbox polling indexes state/next_attempt_at with tenant/account scope. Query indexes must begin with authorized scope where applicable. Financial/audit records must not inherit cache TTL deletion. Actual collections, migrations, transactions and indexes are deferred; no database write is performed by a foundation health probe.

Queues and cancellation are bounded. A canceled caller may already have enqueued a harmless ping; dropping its oneshot reply has no financial effect. Future order cancellation must be a separate reconciled workflow, not inheritance of this ping behavior. No request timeout means an order was canceled. Existing protection must survive pause/outage under Phase 1 rules. These requirements remain unexecuted trading acceptance specifications.

See contracts/storage-interface.md and contracts/secret-manager-interface.md for later storage/custody interfaces. No new service is created for either interface.
