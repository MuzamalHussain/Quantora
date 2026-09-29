# Future acceptance scenarios

Generated readable view of acceptance-tests.json. All scenarios are NOT_RUN; no application exists. Synthetic examples are specification fixtures. Phase 1 checks links and completeness only.

## QNT-AT-0001: Dynamic futures universe

Requirements: QNT-FR-0001. Verification phase: 4. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0001 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Supply a spot-only symbol, an eligible perpetual, and an ineligible contract type; refresh metadata.

Expected observable result: Only the eligible perpetual enters the futures universe; the list changes on refresh without a code change.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0002: Separate scan and execution eligibility

Requirements: QNT-FR-0002. Verification phase: 6. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0002 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Provide a scannable symbol with insufficient history, then excessive spread, then failed model validity.

Expected observable result: The symbol may appear in research scans but each execution attempt is blocked with the specific reason.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0003: Contract lifecycle changes

Requirements: QNT-FR-0003. Verification phase: 4. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0003 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Suspend a symbol with open exposure; change its quantity step while an entry is queued.

Expected observable result: Entry is canceled or blocked, quantities are revalidated, protection/reconciliation and an alert persist; closure failure remains visible.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0004: Required and optional input manifests

Requirements: QNT-FR-0004. Verification phase: 4. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0004 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Remove optional news then required price data under a versioned manifest.

Expected observable result: Optional omission records the selected validated fallback or abstention; missing price blocks entry and exposes the missing input.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0005: Public market data access

Requirements: QNT-FR-0005. Verification phase: 4. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0005 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Open the scanner and paper account with no user integration, then attempt to configure a platform provider as a tenant trader.

Expected observable result: Public features load where feeds are available; provider administration is denied to the trader.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0006: Integration credential lifecycle

Requirements: QNT-FR-0006. Verification phase: 3. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0006 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Exercise each operation as an authorized owner in testnet and inspect the test request audit.

Expected observable result: Masked connection metadata and lifecycle events are returned; no order is created and live credentials/state are unaffected.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0007: Secret storage boundary

Requirements: QNT-FR-0007. Verification phase: 3. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0007 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Submit a synthetic sentinel secret and inspect responses, error paths, telemetry, bundles and database records; deny secret-manager access.

Expected observable result: Sentinel appears only at authorized input/decryption boundaries, ciphertext is stored, outputs are masked, and decryption fails closed without root-key access.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0008: Credential change with exposure

Requirements: QNT-FR-0008. Verification phase: 12. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0008 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Run independent active-position fixtures: replace a key with one for a different account; replace with a valid same-account/environment key; expire or revoke access; remove credentials while exposure remains.

Expected observable result: Wrong-account replacement is rejected. Valid replacement keeps entries frozen until identity, reconciliation and protection handover succeed. Expiry/revocation inhibits new requests under lost authority and alerts the owner. Removal retains unresolved exposure records and manual-intervention status; no case reports FLAT without reconciliation or returns stored plaintext.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0009: Supported integration destinations

Requirements: QNT-FR-0009. Verification phase: 3. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0009 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Submit a loopback URL and a supported provider redirecting to an unapproved host.

Expected observable result: The loopback fetch is blocked before access. A request to the supported initial host may reveal a redirect, but no request reaches the unapproved redirect destination. Both denials have sanitized audit records.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0010: Role authorization

Requirements: QNT-FR-0010. Verification phase: 3. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0010 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Try viewer start/live activation, platform-admin tenant trading, and owner access within its tenant.

Expected observable result: Unauthorized actions return denial without state changes; authorized owner actions remain scoped and audited.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0011: Tenant and environment isolation

Requirements: QNT-FR-0011. Verification phase: 3. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0011 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Tenant A requests tenant B records, object links, websocket channels and job identifiers, including forged tenant IDs.

Expected observable result: No B payload, existence detail or mutation is exposed; each denied boundary is auditable.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0012: Retention export and deletion

Requirements: QNT-FR-0012. Verification phase: 15. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0012 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Export tenant A, request deletion during open exposure and an audit hold, then expire an eligible profile retention period.

Expected observable result: Export excludes other tenants; deletion reports retained categories/reasons and deletes eligible data only; financial links remain restricted and intelligible.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0013: Chart-centered workspace

Requirements: QNT-FR-0013. Verification phase: 11. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0013 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Open a populated session and inspect each panel in PAPER, TESTNET and LIVE fixtures.

Expected observable result: Every named region is present and the mode remains prominent during navigation and modal interactions.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0014: Chart overlays and saved workspace

Requirements: QNT-FR-0014. Verification phase: 11. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0014 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Resize and reload, switch users, then feed a partial fill and moved stop.

Expected observable result: Preferences persist only for the original user and overlays distinguish intended versus executed quantity and current stop.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0015: Bounded chart tools

Requirements: QNT-FR-0015. Verification phase: 11. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0015 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Review implemented indicator/tool inventory and chart dependency license record.

Expected observable result: Only the bounded approved inventory is claimed; distribution is blocked without a verified license decision D-01.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0016: Honest UI status states

Requirements: QNT-FR-0016. Verification phase: 11. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0016 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Freeze feed updates beyond the configured freshness limit while leaving the page open; reconnect with an older event.

Expected observable result: Stale status replaces current status without user refresh, entries are disabled, and old events cannot restore current status.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0017: Built-in virtual account

Requirements: QNT-FR-0017. Verification phase: 11. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0017 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Create a paper session without keys and try settings beyond platform ceilings.

Expected observable result: Valid virtual allocation starts PAPER mode; excessive values are rejected with reasons, and no live route is accessed.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0018: Paper reset epochs

Requirements: QNT-FR-0018. Verification phase: 11. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0018 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Reset an account after wins and losses and inspect both epochs.

Expected observable result: New virtual balance has a distinct epoch, prior history is unchanged, and reports cannot blend epochs into a misleading record.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0019: Execution simulator realism

Requirements: QNT-FR-0019. Verification phase: 8. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0019 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Replay a thin book with a delayed order, partial fill, fee and funding event; repeat using OHLC-only data.

Expected observable result: Book fixture limits fills and accounts for each charge; OHLC result states intrabar ambiguity and cannot claim order-book fill fidelity.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0020: Shared decision logic with separate adapters

Requirements: QNT-FR-0020. Verification phase: 11. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0020 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Run identical versioned inputs/config through paper and a disconnected live adapter; attempt shadow-to-live routing.

Expected observable result: Pre-adapter decisions match; routing isolation denies shadow orders, and records preserve distinct mode tags.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0021: Explicit live activation

Requirements: QNT-FR-0021. Verification phase: 17. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0021 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Attempt activation with testnet success but failed model suitability, then without an authorized action.

Expected observable result: Both attempts are denied with missing gate/authorization reasons; no live order intent is dispatched.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0022: Versioned multi-horizon probabilities

Requirements: QNT-FR-0022. Verification phase: 7. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0022 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Request supported horizons and supply NaN, negative or non-normalized probabilities.

Expected observable result: Valid distributions have separate horizons/versions; invalid distributions are rejected and cannot produce entries.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0023: Reproducible matured labels

Requirements: QNT-FR-0023. Verification phase: 7. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0023 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Evaluate an exact positive/negative threshold boundary, an immature horizon and a missing end price.

Expected observable result: Boundary returns are RANGE under the proposed rule, immature/missing outcomes have no usable label, and original prediction timestamps are unchanged.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0024: Scanner shortlist and context

Requirements: QNT-FR-0024. Verification phase: 6. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0024 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Use tied scores with one illiquid symbol and opposing short/long-horizon evidence.

Expected observable result: Ranking is repeatable, conflicting horizons and exclusion reasons are visible, and shortlist output has no order authority.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0025: Net expected edge admission

Requirements: QNT-FR-0025. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0025 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Use positive gross expected movement but greater round-trip estimated costs, then remove a material fee input.

Expected observable result: Both entries are rejected with net-edge/unknown-cost reasons; no forced trade occurs.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0026: Session lifecycle controls

Requirements: QNT-FR-0026. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0026 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Pause with exposure, attempt resume with stale data, then emergency-stop while disconnected. Restart and restore connectivity while exposure still exists.

Expected observable result: Protection remains active and stale resume is denied. Restart/reconciliation preserves the emergency latch and returns to EMERGENCY_RECOVERY, never RUNNING or PAUSED_PROTECTED while closure remains unresolved. Completion requires reconciled flat settlement; no instantaneous closure claim.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0027: Target and deadline handling

Requirements: QNT-FR-0027. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0027 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Reach target with pending entries; separately reach deadline with a partially filled entry during cancellation. Repeat deadline expiry during PREFLIGHT, BLOCKED and RECOVERING and restart after expiry; repeat recovery with an already persisted target latch.

Expected observable result: No new entry is accepted; late fills create protected residual exposure to close. Deadline/stop/valid-target latches survive every state and restart, with unresolved remote state retained as recovery until safe cancellation/closure is possible. Stale equity cannot newly trigger a target. Final result may be below target and only reconciled settlement ends the session.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0028: Action vocabulary and partial reversal

Requirements: QNT-FR-0028. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0028 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: In one fixture, fill only half a reversal close, then invalidate the opposite signal after closure. In another, fully close and reconcile the old position, approve a fresh opposite opportunity, then partially fill the new entry. Exercise HOLD, REDUCE and TAKE_PROFIT on valid exposure separately.

Expected observable result: Old residual exposure stays protected and no opposite order overlaps it. Invalid opposite opportunity leaves FLAT. An approved second leg has its own cost/risk/intent record, protects only confirmed new quantity and reserves pending quantity. HOLD retains protection; REDUCE and TAKE_PROFIT never exceed confirmed exposure, and their distinct reason/action records persist.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0029: Restart and unknown exposure recovery

Requirements: QNT-FR-0029. Verification phase: 12. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0029 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Terminate after submission but before acknowledgement and restart with an existing exchange position.

Expected observable result: Restart enters RECOVERING, finds the intent/order and actual position, rebuilds protection and does not duplicate the entry.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0030: Manual and external account changes

Requirements: QNT-FR-0030. Verification phase: 12. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0030 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Inject a manual order, deposit and position-mode change during a bot session.

Expected observable result: Discrepancies are recorded; external cash flow is separated from P&L, new bot exposure stops and resolution requires ownership/configuration review.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0031: Single account authority and risk reservation

Requirements: QNT-FR-0031. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0031 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Two sessions simultaneously request the last available risk budget; simulate an expired coordinator resuming.

Expected observable result: At most one reservation succeeds; stale coordinator dispatch is denied, and unknown pending orders retain reserved risk.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0032: Sizing margin and exchange filters

Requirements: QNT-FR-0032. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0032 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Use insufficient margin, a below-minimum rounded quantity and a filter change between sizing and dispatch.

Expected observable result: Each invalid entry is rejected or resized downward and revalidated; dust-close failure enters explicit recovery rather than opening more exposure.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0033: Portfolio ceilings and correlation

Requirements: QNT-FR-0033. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0033 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Offer individually valid orders that together breach a correlated bucket; remove correlation estimates.

Expected observable result: Combined admission fails; fallback reserves conservative exposure, hard ceilings remain unchanged and rejection reasons are logged.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0034: Session equity and cash-flow accounting

Requirements: QNT-FR-0034. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0034 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Start with 1000, deposit 100 and produce no trading P&L; then inject unattributable account activity.

Expected observable result: Target progress remains zero before close costs; unattributable activity blocks target-based claims and triggers reconciliation.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0035: Fill ledger and final results

Requirements: QNT-FR-0035. Verification phase: 12. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0035 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Trade in the correct direction with gross fill P&L +1, fees 1.10 and funding paid 0.10; provide duplicate fill delivery.

Expected observable result: Net realized P&L is -0.20 exactly once; direction success is separate from net outcome, and spread/slippage analytics add no duplicate debit.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0036: Pending cancellation and protection

Requirements: QNT-FR-0036. Verification phase: 12. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0036 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Target termination races with an entry fill and protective-order replacement.

Expected observable result: Residual fill is protected and closed under termination policy; protection is not removed while exposure remains and a failed replacement alerts recovery.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0037: Decision priority and anti-churn

Requirements: QNT-FR-0037. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0037 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: First alternate otherwise eligible bullish/bearish signals within a configured entry cooldown and admission window, with no stop, target or deadline trigger. Then separately repeat with a target and hard stop occurring together.

Expected observable result: In the signal-only fixture, increased-risk entries cannot exceed the configured admission count or bypass cooldown/hysteresis, and rejected signals have reason records. In the conflict fixture, stop/closure takes priority and entries remain inhibited. Necessary exits bypass entry cooldown in both fixtures.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0038: Historical provenance and replay

Requirements: QNT-FR-0038. Verification phase: 5. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0038 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Replay a delisted symbol, missing interval and candle crossing both stop and target without intrabar data.

Expected observable result: The symbol is not silently excluded, the gap is flagged, and the conservative/ambiguous execution rule is recorded without claiming known path.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0039: Data event integrity

Requirements: QNT-FR-0039. Verification phase: 4. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0039 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Deliver the same fill twice and a market sequence gap followed by an older snapshot.

Expected observable result: Fill applies once, gap triggers invalid quality/resync and the old snapshot cannot restore eligibility.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0040: Learning evidence and attribution

Requirements: QNT-FR-0040. Verification phase: 14. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0040 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Provide a correct direction but losing trade, profitable risk breach and untraded matured forecast.

Expected observable result: All are retained; forecast, execution and risk evaluations remain distinct; unsupported causal statements are labelled hypotheses.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0041: Shared-event deduplication and feedback

Requirements: QNT-FR-0041. Verification phase: 14. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0041 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: One forecast reaches 100 users and one user submits fabricated corrective labels.

Expected observable result: Market evidence count remains one, tenant fills stay separate and fabricated feedback does not enter training.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0042: Controlled retraining triggers

Requirements: QNT-FR-0042. Verification phase: 14. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0042 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Observe one matured failure at predicted 70% UP without a drift/evidence trigger. Separately cross an approved sufficient-evidence or drift threshold with validated, deduplicated evidence.

Expected observable result: The isolated failure is recorded without model replacement. Crossing the registered trigger creates an offline candidate job linked to its evidence and trigger version; neither case mutates production weights/code or bypasses promotion and risk gates.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0043: Leakage and selection safeguards

Requirements: QNT-FR-0043. Verification phase: 7. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0043 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Inject a future feature, overlapping train/evaluation horizons and repeated final-holdout tuning.

Expected observable result: Dataset/candidate is quarantined; results are invalidated with provenance and cannot satisfy model gates.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0044: Calibration and suitability evaluation

Requirements: QNT-FR-0044. Verification phase: 10. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0044 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Candidate improves headline net returns but exceeds the drawdown ceiling or fails calibration.

Expected observable result: MODEL_SUITABILITY remains blocked, component metrics and failure reasons are retained, and production remains unchanged.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0045: Auditable promotion and rollback

Requirements: QNT-FR-0045. Verification phase: 14. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0045 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Attempt a candidate promotion lacking shadow evidence, then rehearse rollback from a degraded candidate in a fixture.

Expected observable result: Incomplete promotion is denied; approved rollback restores pinned compatible versions and logs actor/reason without relaxing risk.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0046: Shared models and private account state

Requirements: QNT-FR-0046. Verification phase: 14. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0046 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Two tenants consume one shared forecast with different risk ceilings and replay their decisions.

Expected observable result: Model version is shared, account/risk records remain isolated and each decision reproduces its own permitted quantity.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0047: Readiness gates and honest claims

Requirements: QNT-FR-0047. Verification phase: 11. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0047 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Show a working paper UI driven by a research-only model that fails out-of-sample evaluation.

Expected observable result: Engineering/demo evidence may pass with conspicuous research-only labels; MODEL_SUITABILITY and LIVE_CAPITAL remain blocked.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0048: Operational monitoring and incident recovery

Requirements: QNT-FR-0048. Verification phase: 16. Status: NOT_RUN.

Preconditions: Future implementation of QNT-FR-0048 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Disconnect the exchange, revoke a key and cause a protection gap in an isolated incident drill.

Expected observable result: Each symptom has correlated alert/owner/time evidence; incident is not resolved until exposure and protection reconcile.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0049: Database and technology boundary

Requirements: QNT-FR-0049. Verification phase: 2. Status: NOT_RUN.

Preconditions: Phase 2 architecture proposal and versioned integration evidence register are available for review; no application or live account is required.

Action/input: Review the Phase 2 architecture and authoritative-state inventory.

Expected observable result: MongoDB owns durable application records and ledger intents; proposals are explicitly decided and additional compulsory technology has a documented need.

Method: Document/ADR inspection against each stated obligation, with recorded reviewer findings and disposition; no behavioral execution claim.

## QNT-AT-0050: Current integration verification

Requirements: QNT-FR-0050. Verification phase: 2. Status: NOT_RUN.

Preconditions: Phase 2 architecture proposal and versioned integration evidence register are available for review; no application or live account is required.

Action/input: Inspect integration contract with an unverified order-stream schema and an illustrative fee rate.

Expected observable result: Unverified fields cannot be used as production truth; execution compatibility and cost-validity gates remain blocked until evidence is supplied.

Method: Document/ADR inspection against each stated obligation, with recorded reviewer findings and disposition; no behavioral execution claim.

## QNT-AT-0051: Risk overrides predictions

Requirements: QNT-INV-0001. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0001 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Inject a 99% forecast during a hard-risk breach.

Expected observable result: No increased exposure is admitted; risk-reducing action and breach reason are persisted.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0052: Independent exit and opposite entry

Requirements: QNT-INV-0002. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0002 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Invalidate a SHORT with +$1 unrealized profit and $1.20 total estimated reversal cost.

Expected observable result: Invalid SHORT is submitted for closure even if net closure is a loss; the $1.20 aggregate is not used as an exit veto; opposite entry requires independently available entry-edge/cost evidence.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0053: FLAT and NO TRADE

Requirements: QNT-INV-0003. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0003 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Invalidate the open position when no opposite opportunity exists.

Expected observable result: Close is requested and confirmed exposure becomes FLAT; no replacement entry is submitted.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0054: Invalid SHORT exit

Requirements: QNT-INV-0004. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0004 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Make LONG entry expensive while the SHORT exit criterion remains true.

Expected observable result: SHORT closure proceeds under protection/recovery policy and LONG is rejected with its own reason.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0055: No loss recovery escalation

Requirements: QNT-INV-0005. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0005 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Repeat losses and move the deadline nearer without changing validated market evidence.

Expected observable result: Risk/leverage/frequency ceilings do not rise due to losses, target shortfall or remaining time.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0056: Risk-derived quantity

Requirements: QNT-INV-0006. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0006 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Halve available risk budget with identical prices and stop distance.

Expected observable result: Permitted quantity cannot increase and remains rounded within all constraints.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0057: Stop distinct from liquidation

Requirements: QNT-INV-0007. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0007 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Propose an entry whose only stop is liquidation or whose liquidation buffer is inadequate.

Expected observable result: Entry is denied with missing/inadequate stop reason.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0058: Costs without double counting

Requirements: QNT-INV-0008. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0008 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Reconcile fills with measured slippage and explicit commissions/funding.

Expected observable result: Net ledger equals fill-based P&L minus fees plus signed funding; slippage is attribution only.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0059: Reconcile unknown status

Requirements: QNT-INV-0009. Verification phase: 12. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0009 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Return submission timeout after exchange acceptance but before acknowledgement.

Expected observable result: Intent remains UNKNOWN with reservation; order queries/events resolve it, and no second exposure-increasing order is sent on timeout alone.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0060: Critical-input freshness

Requirements: QNT-INV-0010. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0010 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Stale feed occurs with an open position and existing protection.

Expected observable result: Entries stop, protection remains, stale values are not treated as fresh, and inability to verify/manage exposure is alerted.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0061: Exit bypasses entry cooldown

Requirements: QNT-INV-0011. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0011 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Trigger a stop immediately after an entry cooldown begins.

Expected observable result: Closure is dispatched without waiting for cooldown, unless unknown order state requires reconciliation to avoid increased exposure.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0062: Mode isolation

Requirements: QNT-INV-0012. Verification phase: 12. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0012 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Forge a LIVE route in a shadow or demo event.

Expected observable result: Dispatcher rejects environment/authority mismatch before any exchange request.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0063: Durable intent before dispatch

Requirements: QNT-INV-0013. Verification phase: 12. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0013 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Crash before dispatch, after dispatch and before fill persistence in separate runs.

Expected observable result: Recovery finds durable intents, reconciles actual exchange status, deduplicates effects and neither assumes rollback nor blindly resubmits.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0064: Outage closure limitations

Requirements: QNT-INV-0014. Verification phase: 12. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0014 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Request emergency flatten while exchange requests time out.

Expected observable result: UI and audit retain exposed/unknown recovery state, alert owner and never report CLOSED until reconciled.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0065: LLM authority boundary

Requirements: QNT-INV-0015. Verification phase: 9. Status: NOT_RUN.

Preconditions: Future implementation of QNT-INV-0015 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Supply an LLM response asking to bypass risk and place an order.

Expected observable result: The text cannot mint an authorized order intent or change hard limits; the deterministic pipeline remains authoritative.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0066: Freshness budgets by input and horizon

Requirements: QNT-NFR-0001. Verification phase: 4. Status: NOT_RUN.

Preconditions: Future implementation of QNT-NFR-0001 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Inject ages at the configured limit, just beyond it and a future timestamp beyond skew tolerance.

Expected observable result: At-limit acceptance follows the declared inclusive rule; beyond-limit/future-invalid inputs cannot authorize risk. Reports show age by input and horizon.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0067: Latency measurement

Requirements: QNT-NFR-0002. Verification phase: 10. Status: NOT_RUN.

Preconditions: Future implementation of QNT-NFR-0002 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Run the approved synthetic workload including timeouts and capture traces.

Expected observable result: Every segment has timestamps and distributions; timeouts are counted rather than dropped; unknown budgets block latency readiness claims.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0068: Recovery objectives

Requirements: QNT-NFR-0003. Verification phase: 16. Status: NOT_RUN.

Preconditions: Future implementation of QNT-NFR-0003 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Kill a worker after dispatch and restore a database snapshot with lagging events.

Expected observable result: Measured RTO/RPO and any missing intents/events are reported; no safe-recovery PASS without reconciliation and objective compliance.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0069: Reliability and capacity

Requirements: QNT-NFR-0004. Verification phase: 16. Status: NOT_RUN.

Preconditions: Future implementation of QNT-NFR-0004 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Exceed the approved simultaneous-session and order workload during a feed burst.

Expected observable result: Admission/backpressure occurs without bypassing risk or starving reconciliation; workload and service percentiles are published.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0070: Security and audit completeness

Requirements: QNT-NFR-0005. Verification phase: 16. Status: NOT_RUN.

Preconditions: Future implementation of QNT-NFR-0005 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Inject denied operations, secret sentinels and an audit-record modification.

Expected observable result: No unauthorized mutation or disclosed sentinel; each attempted/accepted operation is attributable and audit tampering is detected.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0071: Reproducibility

Requirements: QNT-NFR-0006. Verification phase: 10. Status: NOT_RUN.

Preconditions: Future implementation of QNT-NFR-0006 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Repeat the same replay twice from immutable manifests.

Expected observable result: Decision IDs/quantities/reasons and ledger values match exactly; numerical model deviations are within declared tolerance or evaluation fails.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0072: Observable and actionable incidents

Requirements: QNT-NFR-0007. Verification phase: 16. Status: NOT_RUN.

Preconditions: Future implementation of QNT-NFR-0007 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Inject one protection gap and one repeated alert storm.

Expected observable result: One correlated incident retains repeat counts and latency measurement, routes to an owner, and stays unresolved until exposure is verified.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## QNT-AT-0073: Accessible responsive UI

Requirements: QNT-NFR-0008. Verification phase: 11. Status: NOT_RUN.

Preconditions: Future implementation of QNT-NFR-0008 is available in an isolated fixture; no real capital or production credentials. Versioned inputs and expected policy configuration are recorded.

Action/input: Navigate by keyboard and inspect the three viewport fixtures with contrast measurement.

Expected observable result: Controls remain operable, mode/protection status remains visible, contrast meets the target and failures block UI readiness.

Method: Automated fixture/integration test with persisted events and rejected-action assertions; reviewer inspects the evidence against this oracle.

## Mandatory scenario coverage index

| Requested scenario | Future test |
|---|---|
| Invalid SHORT +$1 versus $1.20 reversal cost | QNT-AT-0052 |
| No valid opposite opportunity; close then FLAT | QNT-AT-0053 |
| Hard-risk breach with high-confidence prediction | QNT-AT-0051 |
| Rapid alternating signals | QNT-AT-0037 |
| Target with pending entries | QNT-AT-0027 |
| Deadline with partial fills | QNT-AT-0027 |
| Stale feed with open exposure | QNT-AT-0060 |
| Unknown order-submission timeout | QNT-AT-0059 |
| Duplicate fill/event delivery | QNT-AT-0039 |
| Credential replacement/revocation with position | QNT-AT-0008 |
| Cross-tenant access | QNT-AT-0011 |
| Paper reset preserves history | QNT-AT-0018 |
| Correct direction, negative net trade | QNT-AT-0035 |
| One failed 70% forecast | QNT-AT-0042 |
| Shared forecast does not multiply evidence | QNT-AT-0041 |
| Better headline returns but failed drawdown/calibration | QNT-AT-0044 |
| Candidate leakage/contamination | QNT-AT-0043 |
| Restart with exchange exposure | QNT-AT-0029 |
| External/manual order changes | QNT-AT-0030 |
| Symbol suspension/delisting | QNT-AT-0003 |
| Demo/shadow attempts live route | QNT-AT-0062 |
| UI stale data displayed as current | QNT-AT-0016 |
| Secrets in responses/logs | QNT-AT-0007 |
