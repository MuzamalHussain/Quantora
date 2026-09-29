# Measurable nonfunctional requirements

These are acceptance targets/methods, not measured service performance. Canonical QNT-NFR entries are indexed below. Numeric settings requiring experiments are deliberately not presented as proven. Missing approved budgets block the dependent feature, not Phase 2 planning.

| Area | Measurement and acceptance boundary | Owner / decision / deadline |
|---|---|---|
| Freshness | Event age and receive age by price/book/mark/candle/metadata/account/funding/optional source, for each enabled horizon; missing budget or violation inhibits increased risk | Research + systems / D-03 / Phase 4 budgets, before Phase 7 model use |
| Latency | Ingest, features, inference, risk, durable dispatch, exchange acknowledgement and UI segments; p50/p95/p99 with timeouts and sample counts per load interval | Architect / D-04 / Phase 2 definition, Phase 10 measurement |
| RTO/RPO | Detection-to-protected/reconciled service, lost acknowledged records by type; snapshot restore and dispatch crash drills; do not promise exchange availability | Operations / D-05 / Phase 2 targets, Phase 16 proof |
| Reliability/capacity | Available critical-service minutes / eligible scheduled minutes, error/timeout rates, queue lag; defined tenants/symbols/concurrent sessions/pending orders; soak and overload admission | Product + operations / D-06 / Phase 2 envelope, Phase 16 proof |
| Security/audit | Zero unauthorized mutations/secret disclosures in fixture suite; all security/financial changes attributable; tampering detected | Security / QNT-NFR-0005 / Phase 16 |
| Reproducibility | Exact deterministic decisions/ledger on pinned manifests; prespecified tolerance only for stochastic numeric model outputs | Research / QNT-NFR-0006 / Phase 10 |
| Alerting | Detection/notification/acknowledgement delay, storm deduplication, incident owner and resolution evidence | Operations / D-07 / Phase 16 |
| UI | Keyboard access, visible focus, >=4.5:1 proposed text contrast; 360/768/1440 CSS-pixel widths; no color-only risk cues | Frontend + product / D-14 / Phase 2 target, Phase 11 proof |

Exchange outage periods are reported separately and included in user-visible availability impact; exclusions cannot hide failures. A metric report identifies environment, build, clock source, workload, sample duration, p50/p95/p99 and failures. No unapproved percentile target can be marked passed. Raw latency samples retain error/timeout cases rather than only successful requests. Research horizon length does not serve as a latency budget.


- **QNT-NFR-0001** — Freshness budgets by input and horizon; acceptance QNT-AT-0066.
- **QNT-NFR-0002** — Latency measurement; acceptance QNT-AT-0067.
- **QNT-NFR-0003** — Recovery objectives; acceptance QNT-AT-0068.
- **QNT-NFR-0004** — Reliability and capacity; acceptance QNT-AT-0069.
- **QNT-NFR-0005** — Security and audit completeness; acceptance QNT-AT-0070.
- **QNT-NFR-0006** — Reproducibility; acceptance QNT-AT-0071.
- **QNT-NFR-0007** — Observable and actionable incidents; acceptance QNT-AT-0072.
- **QNT-NFR-0008** — Accessible responsive UI; acceptance QNT-AT-0073.
