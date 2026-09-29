# Product scope and architecture boundary

Quantora is a multi-user SaaS for Binance USDT-margined perpetual discovery, scanning, probabilistic forecasting, deterministic risk, position management, paper trading and eventually controlled live execution. The decision chain is metadata -> eligible scan universe -> features/context -> multi-horizon probabilities/movement/uncertainty -> cost-adjusted opportunity -> deterministic risk reservation -> authorized execution adapter -> reconciliation/ledger -> evaluation.

The pipeline can validly produce NO_TRADE or FLAT. Target profit is a stopping condition, never a guaranteed result. No component may increase risk, leverage or frequency merely because of losses, target shortfall or time pressure. See QNT-INV-0001 through QNT-INV-0015.

Initial scope includes the dashboard, Settings > Integrations, virtual account, governed learning and recovery-aware lifecycle. Macro/news are optional awareness inputs with evaluated missing-data behavior. Spot inclusion is not futures eligibility. Multiple exchanges, full TradingView parity, high-frequency/latency promises, deep learning, guaranteed profitability and immediate autonomous online weight mutation are excluded.

MongoDB is the confirmed primary application database. Durable application intent, ledger and audit responsibilities cannot be delegated to a disposable Redis cache. Separate services/languages and Parquet/object storage are proposed choices for Phase 2 (D-02), not a scaffold created here. No compulsory PostgreSQL, Kafka or ClickHouse is introduced.

Trust boundaries: browser handles input/display but not trading authority; authenticated API resolves tenant/environment; forecasting produces evidence only; deterministic risk authorizes bounded intents; account coordinator serializes exposure; execution adapter handles a specific environment; reconciler observes exchange truth; ledger records reconciled effects. Research jobs cannot call live dispatch. LLM text cannot authorize orders. Secret manager root keys are outside the encrypted-credential database.

This phase produces an implementation contract and a structural validator only. All implementation phases 2–18 remain NOT_STARTED. Proposed numerical thresholds/defaults remain deferred with named role owners; those roles are responsibilities to assign, not invented named approvals.
