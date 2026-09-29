# Dashboard and API settings

QNT-FR-0006–0009 and 0013–0021 are the canonical requirements. The workspace is chart-centered, not a promise of TradingView feature or library rights. Chart selection/license is D-01 in Phase 2.

Top bar: selected instrument, connection/freshness age, session equity/P&L with simulated/research labels and persistent PAPER / TESTNET / LIVE indicator. Center: candles, volume, timeframe selector and approved indicators, with separate intended-entry, executed-trade, stop and target overlays. Left: symbol search, watchlists and scanner with execution-ineligibility reasons. Right: start/pause/resume/stop/emergency controls, forecast horizons/probabilities/uncertainty, evidence and bounded risk settings. Bottom: positions, pending orders, fills/history, sanitized logs and net performance attribution.

Proposed initial indicators: SMA, EMA, RSI, MACD and ATR alongside volume. Drawings: horizontal line, trend line and rectangle. Parameters and preferences are per-user persisted values, not hidden global state. Full scripting, marketplace indicators and proprietary TradingView integration are outside initial scope. Mobile panels may collapse into tabs but mode, exposure and emergency action stay reachable. QNT-NFR-0008 contains proposed contrast/keyboard/viewport acceptance.

Each panel handles loading, no results, disconnected, stale and error explicitly. A stale chart can remain visible with an age/warning, but cannot show a current badge. An entry-ineligible instrument can remain discoverable with its reason. Unknown order state is displayed as unresolved exposure risk, never a zero position. Estimated P&L, net target progress and final settled P&L are distinct labels.

Settings > Integrations lists provider/environment, masked key identifier, health, permissions, last safe test and key version, never saved plaintext. Owner-only add/test/replace/revoke/disconnect/remove controls use supported providers rather than freeform URLs. Replacement tests account identity and protection handover; disconnect describes outstanding exposure and manual recovery when account access is lost. User keys and administrator-owned data-provider keys have distinct screens/permissions. Errors and clipboard/export features do not reveal secrets. Connection tests make no trades.

A live activation dialog identifies account/environment and gate state; explicit owner action is required. Changing a UI tab, resetting paper balance, connecting testnet or inspecting a forecast cannot activate real-money execution.
