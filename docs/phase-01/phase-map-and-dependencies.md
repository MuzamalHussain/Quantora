# Phase map and release dependencies

The phase rows below are a view of requirements.json. Dependency edges express prerequisite deliverables, not a rule requiring every earlier numbered phase to finish. Phase 3 SaaS and Phase 4 ingestion can proceed independently after Phase 2; Phase 8 simulation and Phase 7 research have separate work streams. Cross-cutting invariant IDs are design constraints; depending on one does not mean its full final integration test must precede design work. Late verification phases check integrated behavior.

| Phase | Name | Prerequisite phases | Status |
|---|---|---|---|
| 1 | Requirements and scope | None | PASS |
| 2 | Architecture and foundation | 1 | NOT_STARTED |
| 3 | SaaS and data foundation | 2 | NOT_STARTED |
| 4 | Binance market ingestion | 2 | NOT_STARTED |
| 5 | Historical data and replay | 4 | NOT_STARTED |
| 6 | Features and market scanner | 4 | NOT_STARTED |
| 7 | Forecasting and calibration | 5, 6 | NOT_STARTED |
| 8 | Costs and execution simulator | 5 | NOT_STARTED |
| 9 | Risk and position decisions | 2, 6, 8 | NOT_STARTED |
| 10 | Integrated strategy validation | 7, 8, 9 | NOT_STARTED |
| 11 | User demo and trading workspace | 3, 4, 8, 9 | NOT_STARTED |
| 12 | Binance execution integration | 3, 4, 9 | NOT_STARTED |
| 13 | Forward and shadow validation | 10, 11, 12 | NOT_STARTED |
| 14 | Controlled self-learning | 7, 10, 13 | NOT_STARTED |
| 15 | SaaS product completion | 3, 11 | NOT_STARTED |
| 16 | Security and operational readiness | 3, 9, 12, 15 | NOT_STARTED |
| 17 | Controlled live pilot | 10, 13, 14, 16 | NOT_STARTED |
| 18 | Production and gradual expansion | 17 | NOT_STARTED |

Requirement-specific prerequisite IDs, primary implementation phase, verification phases and blocked release gates are in requirements.json/traceability.csv. Primary phase identifies where the contract is principally delivered; supporting design may occur earlier, and verification may occur in several later phases. A test's verification_phase is the first planned behavioral verification context, with further integration checks listed on the requirement.

ENGINEERING: structural services and deterministic lifecycle can function. MODEL_SUITABILITY: research evidence meets pre-registered selection, leakage, calibration, cost and risk standards. USER_DEMO: users can operate the labelled paper account safely. LIVE_CAPITAL: all relevant engineering, research, demo, integration, forward, governance and operational evidence plus owner activation is required. These gates are independent evidence records; all implementation gates currently have no executed evidence. The phase-01 PASS is not one of these implementation release gates.

Phase 13 consumes Phase 10 strategy validation, Phase 11 paper and Phase 12 exchange compatibility. Phase 14 adds governed retraining/promotion evidence. Phase 16 verifies security/operations against assembled services. Phase 17 remains blocked until these and model suitability pass. Phase 18 requires controlled-pilot evidence and a separate expansion decision. A failed research gate does not prevent a clearly labelled research-only engineering demo; it does prevent live promotion.

Phase dependency edges require the named engineering artifacts, not automatic PASS of every release gate attached to those artifacts. For example, Phase 13 can exercise an internal, unreleased Phase 11 paper workspace while Phase 16 operational evidence is pending. Phase 10 produces initial model-evaluation evidence; the final MODEL_SUITABILITY gate for a promoted model also needs applicable Phase 14 governance evidence. This avoids treating Phase 13 as requiring a completed Phase 14 promotion. An internal demo is not a released USER_DEMO service: final USER_DEMO readiness still requires all attached requirements, including later security/recovery checks. Live-capital eligibility never inherits a provisional/internal-demo result. No requirement or gate is waived by this scheduling distinction.
