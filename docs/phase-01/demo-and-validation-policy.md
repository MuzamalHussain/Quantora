# Demo and validation policy

| Mode | Inputs and execution | Evidence it can provide | Cannot establish |
|---|---|---|---|
| Historical replay/backtest | Point-in-time historical data, simulated fills | Reproducibility, historical sensitivity and strategy diagnostics | Future profitability or actual routing reliability |
| Built-in live-market paper | Real feeds, virtual balance, simulated adapter | User demo and forward simulated decision/behavior evidence | Real fill fidelity without validated simulation |
| Binance demo/testnet | Separately verified test endpoint/account | Adapter compatibility and account lifecycle | Profitability or equivalence of liquidity/costs to live |
| Shadow | Real-time forecasts/decisions, no orders | Drift, forecast and decision comparison | Executed returns |
| LIVE | Authorized real venue account | Controlled pilot outcomes with actual fills | Guaranteed future returns |

QNT-FR-0017–0021, 0040–0047 and the trading invariants apply. The paper account shares versioned forecasting and deterministic risk logic with live through a different execution adapter. Unsupported simulated effects are shown in every relevant report. A reset creates a new epoch without deleting prior wins/losses. Target shortfall is acceptable; a risk breach is not.

Engineering gate: service contracts, isolation, reconciliation and deterministic fixtures verified. Model suitability gate: pre-registered backtest/time-separated evaluation, uncertainty/calibration/cost/risk tests passed against baselines. User-demo gate: working, accessible, labelled virtual account and workspace with safe simulation/risk handling. Live-capital gate: model suitability plus integration, forward/shadow, security/operations, controlled promotion and explicit owner activation. No gate is earned in Phase 1 except the documentation baseline itself.

A research-only model can support an engineering/user demo if probabilities and outcomes are conspicuously labelled unvalidated research and all deterministic risk/mode safeguards work. Failed model gates remain a hard block to live promotion and validated-performance claims. Thresholds, sample sizes, confidence methods, cost stresses and forward observation windows are D-09 and must be fixed before evaluation, not chosen after favorable results.

All acceptance-tests.json entries are future specifications and NOT_RUN. Their synthetic inputs are not market observations. Each future run must retain build/version, fixture/config, timestamp, actual observed output, logs and independent review where required. Structural validation of these files does not execute any of them.
