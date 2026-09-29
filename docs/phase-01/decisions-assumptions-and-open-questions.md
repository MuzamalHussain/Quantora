# Decisions, assumptions and open questions

Canonical deferred decisions are structured in requirements.json.decisions. All are DEFERRED and NOT_APPROVED. Role owners must be assigned during the listed phase. These do not prevent Phase 2 from beginning architecture decisions; each dependent commitment/capability remains blocked until resolved. No product approval is inferred from this document.

## D-01: Chart engine, license and tool scope

Owner: Frontend lead. Resolution phase: 2. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Bounded indicator/drawing inventory in QNT-FR-0015; engine unspecified.

Resolution method: Compare maintained engines, official licenses and feature prototypes; record redistribution terms and approve inventory.

Blocked consequence: Blocks chart-library commitment/distribution; does not block architecture planning.

## D-02: Runtime and durable-state design

Owner: Systems architect. Resolution phase: 2. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Rust core, Python research/APIs, React/TypeScript, optional Redis, Parquet/object storage and Linux containers; MongoDB is confirmed.

Resolution method: ADR for deployment, durability/write concerns, indexes, decimal representation, fenced ownership and outbox/reconciliation; no second required database.

Blocked consequence: Blocks implementation foundation choices and exchange dispatch.

## D-03: Freshness, horizons and label parameters

Owner: Research lead + trading systems lead. Resolution phase: 4. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Candidate horizons 5m, 15m, 1h, 4h; entry on completed bars with live execution quotes; inclusive age limit.

Resolution method: Measure event/receive delays and gap rates per feed across quiet/busy periods; choose age/skew thresholds per input/horizon, theta and maturity price rules before use.

Blocked consequence: Blocks enabled decision horizons until budget and feature manifests are set; label parameters must be frozen before Phase 7 fitting.

## D-04: Latency budgets and timing instrumentation

Owner: Systems architect. Resolution phase: 2. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: No proven latency numbers; human horizon differs from processing time.

Resolution method: Design traces in Phase 2; benchmark warm/cold and overloaded paths by Phase 10 and freeze segment budgets before readiness evaluation.

Blocked consequence: Blocks claimed latency SLOs and latency-sensitive strategy admission.

## D-05: RTO/RPO by record class

Owner: Operations lead. Resolution phase: 2. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Proposed zero loss of acknowledged durable financial intents; caches can rebuild; exchange outages excluded from guaranteed closure time.

Resolution method: Select durability/backup topology, declare RTO and RPO for intents/fills/config/history; fault injection and restore drill measure loss and elapsed recovery.

Blocked consequence: Blocks recovery design signoff; measured compliance required in Phase 16 before live.

## D-06: Reliability and capacity envelope

Owner: Product owner + operations lead. Resolution phase: 2. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: No tenant or throughput claim yet.

Resolution method: Approve target tenants, symbols, concurrent sessions/orders and workload duration; define availability/error budgets and run soak/overload tests.

Blocked consequence: Blocks capacity promises; Phase 16 load evidence required for live.

## D-07: Alert severity and response budgets

Owner: Operations lead. Resolution phase: 16. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Protection gap, credential loss with exposure and unknown order status are critical.

Resolution method: Assign on-call coverage; set detection/notification/acknowledgement objectives and measure drills, including unreachable owner escalation.

Blocked consequence: Blocks operational readiness/live.

## D-08: Risk ceilings and account ownership policy

Owner: Risk owner + product owner. Resolution phase: 9. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: One bot writer per account/environment; dedicated account, one-way isolated positions initially; external trading freezes entries.

Resolution method: Stress correlated shocks, gaps, fees and concurrency; approve numeric risk/leverage/stop buffer/cooldown limits and permitted account modes without modifying user exchange settings automatically.

Blocked consequence: Blocks enabled trading decisions even in paper until fixture-safe configuration; blocks live until approved.

## D-09: Forecast, liquidity and promotion thresholds

Owner: Research lead + independent risk reviewer. Resolution phase: 7. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Simple baselines before complex models; cost-aware net-edge threshold and prespecified calibration/drawdown constraints.

Resolution method: Pre-register sample counts, horizon/symbol coverage, baselines, cost stress, confidence intervals, evidence/drift triggers; final paper/shadow duration and promotion criteria frozen before Phase 13.

Blocked consequence: Blocks model suitability/live claims; research-only demo remains possible with configured safe risk.

## D-10: Exchange capabilities and test environment

Owner: Exchange integration lead. Resolution phase: 2. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Verify testnet/demo endpoints, account modes, protective/algo orders, user streams, signing, limits and regional/provider availability.

Resolution method: Use official current documentation and dated fixtures; user-stream page did not expose its schema during Phase 1 verification. Recheck all assumed behavior before implementation.

Blocked consequence: Blocks reliance on unverified endpoints/modes; Phase 12 compatibility proof required before dispatch eligibility.

## D-11: Provider fees, history and usage rights

Owner: Data owner. Resolution phase: 5. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Account-specific commission/funding assumptions; optional news/macro only with approved provenance.

Resolution method: Verify official provider availability, rate limits, retention and redistribution/training rights; quantify missing depth/history and model cost sensitivity.

Blocked consequence: Blocks performance claims using unknown costs/coverage or unlicensed data.

## D-12: Retention and lawful-use policy

Owner: Privacy/security owner + product owner. Resolution phase: 3. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Separate erasable profile/preferences from restricted financial/audit history; tenant data is not shared training data by default.

Resolution method: Define operating jurisdictions, retention durations, holds, consent and trained-artifact deletion handling with appropriate review; no legal compliance claim in Phase 1.

Blocked consequence: Blocks production tenant data collection/export/deletion promises until durations and authority are decided.

## D-13: Default session behavior and accounting conventions

Owner: Product owner + risk owner. Resolution phase: 9. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Pause retains protection; stop/target/deadline flatten; close-first reversal; target net of estimated close costs; no pause clock extension.

Resolution method: Approve state/accounting tables and deterministic fixtures before Phase 9 release; user target remains a stopping condition.

Blocked consequence: Blocks production session configuration defaults; architecture can support the explicit proposed contracts now.

## D-14: UI accessibility target

Owner: Product owner + frontend lead. Resolution phase: 2. Status: DEFERRED; approval: NOT_APPROVED.

Proposal: Contrast and viewport targets in QNT-NFR-0008 are proposed product requirements, not a certified standards claim.

Resolution method: Review with keyboard/mobile prototypes and approve acceptance thresholds.

Blocked consequence: Blocks final UI acceptance target signoff.

## Confirmed decisions and non-assumptions

Confirmed by this request: Binance Futures USDT-margined perpetual initial scope; MongoDB primary database; multi-user SaaS and user-configured integrations; virtual account; controlled learning; independent close/re-entry and all 15 invariants; preserve the 18-phase map. No exchange account permissions, proprietary library rights, production model quality, fee rate, history completeness or specific throughput is assumed. The empty starting workspace required no document migration or reconciliation.
