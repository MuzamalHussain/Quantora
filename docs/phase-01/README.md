# QUANTORA: Phase 1 baseline

Status: PASS for requirements and registry consistency only. This is a new project.
No prior platform code, counts, evidence or approvals were imported. Workspace inspection found no existing files or applicable ancestor AGENTS.md files to reconcile.

Read product-scope.md, state-machines-and-accounting.md and phase-map-and-dependencies.md first.
requirements.json is the sole canonical normative registry. Markdown documents explain its contracts; generated requirement indexes repeat titles/links only. acceptance-tests.json is the canonical future acceptance specification; acceptance-scenarios.md is its generated readable view. traceability.csv is derived from the registry.

Origin USER_CONFIRMED means supplied in this project's request, not independently approved implementation detail. INHERITED_INVARIANT means one of the 15 invariants supplied in this request, not inheritance from an older project. PROPOSED is explicitly not user approval. SPECIFIED/PROPOSED describe requirements, never implemented behavior.

Run from any directory:

```powershell
python C:/Users/paren/OneDrive/Desktop/Quantora/scripts/validate_phase01.py
```

The validator checks schema/reference/traceability integrity, not behavior or semantic completeness. Future tests are NOT_RUN. See phase-01-report.md for actual results, semantic review and blocking decisions. Update canonical JSON first, then synchronize its readable views and CSV when changing the baseline. No application scaffold or dependency installation belongs in this phase.

The original baseline was authored on 2026-09-13. The 2026-09-15 continuation preserves it and is tracked in [continuation-checkpoint.md](continuation-checkpoint.md), including current validation and the exact next action. The validator also checks the readable acceptance, decision and phase views against their canonical fields. A structural PASS does not substitute for the separate semantic review in the report.

Validator regression checks are reproducible with `python scripts/test_validate_phase01.py` from the workspace root. These checks validate isolated document copies and never execute application/trading scenarios.
