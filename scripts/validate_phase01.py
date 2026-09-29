#!/usr/bin/env python3
"""Validate QUANTORA Phase 1 registry consistency; never executes trading tests.

Standard library only. --root permits validation of a copied baseline.
Exit 0 = structurally consistent; exit 1 = validation failures.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

REQUIRED_DOCS = '''README.md product-scope.md user-flows-and-permissions.md
functional-requirements.md nonfunctional-requirements.md trading-invariants.md
state-machines-and-accounting.md data-and-integration-contracts.md
dashboard-and-api-settings.md demo-and-validation-policy.md
self-learning-and-model-governance.md security-and-tenant-isolation.md
phase-map-and-dependencies.md decisions-assumptions-and-open-questions.md
sources.md acceptance-scenarios.md requirements.json acceptance-tests.json
traceability.csv phase-01-report.md'''.split()
CONTINUATION_DOCS = ['continuation-checkpoint.md']
REQ_FIELDS = '''id title normative_requirement category priority origin
primary_implementation_phase verification_phases dependency_ids
acceptance_test_ids release_gate status'''.split()
TEST_FIELDS = '''id linked_requirement_ids scenario preconditions action_input
expected_observable_result verification_method verification_phase execution_status'''.split()
CSV_FIELDS = '''requirement_id primary_implementation_phase prerequisite_phases
verification_phases dependency_ids acceptance_test_ids release_gate status'''.split()
PHASE_NAMES = ['Requirements and scope', 'Architecture and foundation',
    'SaaS and data foundation', 'Binance market ingestion', 'Historical data and replay',
    'Features and market scanner', 'Forecasting and calibration', 'Costs and execution simulator',
    'Risk and position decisions', 'Integrated strategy validation', 'User demo and trading workspace',
    'Binance execution integration', 'Forward and shadow validation', 'Controlled self-learning',
    'SaaS product completion', 'Security and operational readiness', 'Controlled live pilot',
    'Production and gradual expansion']
GATES = {'ENGINEERING', 'MODEL_SUITABILITY', 'USER_DEMO', 'LIVE_CAPITAL'}


def validate(root):
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    base = root / 'docs' / 'phase-01'
    for rel in [*(Path('docs/phase-01') / n for n in REQUIRED_DOCS + CONTINUATION_DOCS), Path('scripts/validate_phase01.py')]:
        path = root / rel
        check(path.is_file() and path.stat().st_size > 0, f'Missing/empty required file: {rel}')
    def read_json(name):
        try:
            obj = json.loads((base / name).read_text(encoding='utf-8'))
            if not isinstance(obj, dict):
                raise ValueError('top level must be an object')
            return obj
        except (OSError, ValueError) as exc:
            errors.append(f'{name}: {exc}')
            return {}
    registry, acceptance = read_json('requirements.json'), read_json('acceptance-tests.json')
    check(registry.get('project') == 'QUANTORA', 'Wrong project')
    check(registry.get('schema_version') == 1 and acceptance.get('schema_version') == 1, 'Unsupported schema version')
    check(registry.get('phase_01_status') in {'PASS', 'BLOCKED', 'IN_REVIEW'}, 'Invalid Phase 1 status')

    def objects(obj, key):
        data = obj.get(key)
        if not isinstance(data, list) or not data:
            errors.append(f'{key} must be a nonempty list')
            return []
        check(all(isinstance(x, dict) for x in data), f'{key} entries must be objects')
        return [x for x in data if isinstance(x, dict)]
    reqs, tests = objects(registry, 'requirements'), objects(acceptance, 'acceptance_tests')
    phases, decisions = objects(registry, 'phases'), objects(registry, 'decisions')

    def phase(n):
        return type(n) is int and 1 <= n <= 18
    def ids(rows, pattern, label):
        result = {}
        for row in rows:
            key = row.get('id')
            if not isinstance(key, str) or not re.fullmatch(pattern, key):
                errors.append(f'{label} invalid ID: {key!r}')
                continue
            check(key not in result, f'Duplicate {label} ID: {key}')
            result[key] = row
        return result
    rmap = ids(reqs, r'QNT-(?:FR|NFR|INV)-\d{4}', 'requirement')
    tmap = ids(tests, r'QNT-AT-\d{4}', 'acceptance')
    dmap = ids(decisions, r'D-\d{2}', 'decision')

    def string_fields(row, fields, label):
        for key in fields:
            check(isinstance(row.get(key), str) and bool(row[key].strip()), f'{label}: missing/empty string {key}')
    def list_field(row, key, label, allow_empty=False):
        value = row.get(key)
        if not isinstance(value, list):
            errors.append(f'{label}: {key} must be a list')
            return []
        check(bool(value) or allow_empty, f'{label}: empty {key}')
        check(len(value) == len({json.dumps(x, sort_keys=True) for x in value}), f'{label}: duplicate values in {key}')
        return value

    pmap = {}
    for p in phases:
        num = p.get('phase')
        if not phase(num):
            errors.append(f'Invalid phase number {num!r}')
            continue
        check(num not in pmap, f'Duplicate phase {num}')
        pmap[num] = p
        check(p.get('name') == PHASE_NAMES[num-1], f'Phase {num} name does not preserve map')
        check(p.get('status') == ('PASS' if registry.get('phase_01_status') == 'PASS' else registry.get('phase_01_status')) if num == 1 else p.get('status') == 'NOT_STARTED', f'Invalid Phase {num} status (later phases must be NOT_STARTED)')
        for dep in list_field(p, 'prerequisite_phases', f'Phase {num}', True):
            check(phase(dep) and dep != num, f'Phase {num}: invalid prerequisite {dep}')
    check(set(pmap) == set(range(1, 19)), 'Exactly phases 1–18 are required')

    for r in reqs:
        label = str(r.get('id'))
        check(all(k in r for k in REQ_FIELDS), f'{label}: mandatory field missing')
        string_fields(r, ['id','title','normative_requirement','category','priority','origin','status'], label)
        check(r.get('priority') in {'MUST','SHOULD','COULD'}, f'{label}: invalid priority')
        check(r.get('origin') in {'USER_CONFIRMED','INHERITED_INVARIANT','PROPOSED'}, f'{label}: invalid origin')
        check(r.get('status') in {'SPECIFIED','PROPOSED'}, f'{label}: invalid requirement status')
        check((r.get('origin') == 'PROPOSED') == (r.get('status') == 'PROPOSED'), f'{label}: proposal/status mismatch')
        check(phase(r.get('primary_implementation_phase')), f'{label}: invalid primary phase')
        for vp in list_field(r, 'verification_phases', label):
            check(phase(vp), f'{label}: invalid verification phase {vp}')
        for dep in list_field(r, 'dependency_ids', label, True):
            check(isinstance(dep, str) and dep in rmap and dep != r.get('id'), f'{label}: invalid dependency {dep}')
        for tid in list_field(r, 'acceptance_test_ids', label):
            check(isinstance(tid, str) and tid in tmap, f'{label}: missing acceptance {tid}')
            if isinstance(tid, str) and tid in tmap:
                links = tmap[tid].get('linked_requirement_ids', [])
                check(isinstance(links, list) and r.get('id') in links, f'{label}/{tid}: missing reciprocal coverage')
        for gate in list_field(r, 'release_gate', label):
            check(isinstance(gate, str) and gate in GATES, f'{label}: invalid gate {gate}')

    for t in tests:
        label = str(t.get('id'))
        check(all(k in t for k in TEST_FIELDS), f'{label}: mandatory field missing')
        string_fields(t, ['id','scenario','preconditions','action_input','expected_observable_result','verification_method'], label)
        check(phase(t.get('verification_phase')), f'{label}: invalid verification phase')
        check(t.get('execution_status') == 'NOT_RUN', f'{label}: behavioral results cannot be claimed in Phase 1')
        for rid in list_field(t, 'linked_requirement_ids', label):
            check(isinstance(rid, str) and rid in rmap, f'{label}: missing linked requirement {rid}')
            if isinstance(rid, str) and rid in rmap:
                links = rmap[rid].get('acceptance_test_ids', [])
                check(isinstance(links, list) and t.get('id') in links, f'{label}/{rid}: missing reciprocal test link')
                vps = rmap[rid].get('verification_phases', [])
                check(isinstance(vps, list) and t.get('verification_phase') in vps, f'{label}/{rid}: incompatible verification phase')

    for d in decisions:
        label = str(d.get('id'))
        string_fields(d, ['id','title','owner','consequence','proposal','measurement_or_resolution_method'], label)
        check(phase(d.get('resolution_phase')), f'{label}: invalid resolution phase')
        check(d.get('status') == 'DEFERRED' and d.get('approval') == 'NOT_APPROVED', f'{label}: unexpected decision approval/status')

    def acyclic(graph, label):
        seen, visiting = set(), set()
        def visit(node):
            if node in visiting:
                errors.append(f'{label} dependency cycle at {node}')
                return
            if node in seen:
                return
            visiting.add(node)
            for dep in graph.get(node, []):
                if isinstance(dep, (str, int)) and dep in graph:
                    visit(dep)
            visiting.remove(node)
            seen.add(node)
        for node in graph:
            visit(node)
    acyclic({k:r.get('dependency_ids', []) if isinstance(r.get('dependency_ids'),list) else [] for k,r in rmap.items()}, 'Requirement')
    acyclic({k:p.get('prerequisite_phases', []) if isinstance(p.get('prerequisite_phases'),list) else [] for k,p in pmap.items()}, 'Phase')

    try:
        with (base/'traceability.csv').open(encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            check(reader.fieldnames == CSV_FIELDS, 'Traceability columns differ from schema')
            rows = list(reader)
        found = set()
        def join(value):
            return ';'.join(map(str, value)) if isinstance(value, list) else '<invalid>'
        for row in rows:
            rid = row.get('requirement_id')
            check(rid not in found, f'Duplicate traceability row: {rid}')
            found.add(rid)
            if rid not in rmap:
                errors.append(f'Unknown traceability requirement {rid}')
                continue
            r = rmap[rid]
            primary = r.get('primary_implementation_phase')
            prereqs = pmap.get(primary, {}).get('prerequisite_phases', []) if phase(primary) else []
            expected = dict(requirement_id=rid, primary_implementation_phase=str(primary),
                prerequisite_phases=join(prereqs), status=r.get('status'),
                **{key:join(r.get(key)) for key in CSV_FIELDS[3:-1]})
            check(row == expected, f'Traceability mismatch: {rid}')
        check(found == set(rmap), 'Traceability does not cover exactly all requirements')
    except (OSError, csv.Error) as exc:
        errors.append(f'traceability.csv: {exc}')

    # All stable IDs cited in prose must resolve; generated views must cover each entry.
    for name in REQUIRED_DOCS + CONTINUATION_DOCS:
        if not name.endswith('.md') or not (base/name).is_file():
            continue
        text = (base/name).read_text(encoding='utf-8')
        check(text.lstrip().startswith('# '), f'{name}: missing document title (possible truncation)')
        for key in re.findall(r'QNT-(?:FR|NFR|INV|AT)-\d{4}', text):
            check(key in rmap or key in tmap, f'{name}: unknown registry ID {key}')
    for name, mapping in [('functional-requirements.md',{k:v for k,v in rmap.items() if k.startswith('QNT-FR-')}),
                          ('trading-invariants.md',{k:v for k,v in rmap.items() if k.startswith('QNT-INV-')}),
                          ('nonfunctional-requirements.md',{k:v for k,v in rmap.items() if k.startswith('QNT-NFR-')}),
                          ('acceptance-scenarios.md',tmap)]:
        text = (base/name).read_text(encoding='utf-8') if (base/name).is_file() else ''
        for key in mapping:
            check(key in text, f'{name}: missing indexed entry {key}')

    # Check actual readable fields, not merely the presence of each stable ID.
    def markdown(name):
        return (base/name).read_text(encoding='utf-8') if (base/name).is_file() else ''
    def blocks(text, pattern):
        found = {}
        for match in re.finditer(pattern, text, re.M | re.S):
            key = match.group(1)
            check(key not in found, f'Duplicate readable section: {key}')
            found[key] = match.group(0).strip()
        return found
    scenario_blocks = blocks(markdown('acceptance-scenarios.md'), r'^## (QNT-AT-\d{4}):.*?(?=^## |\Z)')
    check(set(scenario_blocks) == set(tmap), 'Readable acceptance sections differ from registry IDs')
    for tid, t in tmap.items():
        links = t.get('linked_requirement_ids', [])
        if not isinstance(links, list) or not all(isinstance(x, str) for x in links):
            continue
        expected = (f"## {tid}: {t.get('scenario')}\n\n"
            f"Requirements: {', '.join(links)}. Verification phase: {t.get('verification_phase')}. Status: {t.get('execution_status')}.\n\n"
            f"Preconditions: {t.get('preconditions')}\n\n"
            f"Action/input: {t.get('action_input')}\n\n"
            f"Expected observable result: {t.get('expected_observable_result')}\n\n"
            f"Method: {t.get('verification_method')}")
        check(scenario_blocks.get(tid) == expected, f'{tid}: readable acceptance content differs from canonical test')
    decision_blocks = blocks(markdown('decisions-assumptions-and-open-questions.md'), r'^## (D-\d{2}):.*?(?=^## |\Z)')
    check(set(decision_blocks) == set(dmap), 'Readable decision sections differ from registry IDs')
    for did, d in dmap.items():
        expected = (f"## {did}: {d.get('title')}\n\n"
            f"Owner: {d.get('owner')}. Resolution phase: {d.get('resolution_phase')}. Status: {d.get('status')}; approval: {d.get('approval')}.\n\n"
            f"Proposal: {d.get('proposal')}\n\n"
            f"Resolution method: {d.get('measurement_or_resolution_method')}\n\n"
            f"Blocked consequence: {d.get('consequence')}")
        check(decision_blocks.get(did) == expected, f'{did}: readable decision content differs from canonical decision')
    phase_rows = re.findall(r'^\| (\d+) \| (.*?) \| (.*?) \| (.*?) \|$', markdown('phase-map-and-dependencies.md'), re.M)
    expected_rows = [(str(n), p.get('name'), ', '.join(map(str,p.get('prerequisite_phases',[]))) or 'None', p.get('status'))
                     for n,p in sorted(pmap.items()) if isinstance(p.get('prerequisite_phases'), list)]
    check(phase_rows == expected_rows, 'Readable phase map differs from canonical phase rows')
    return errors, len(reqs), len(tests), len(decisions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        errors, nr, nt, nd = validate(args.root.resolve())
    except (TypeError, ValueError, KeyError, RecursionError, OSError) as exc:
        print(f'FAIL: malformed baseline: {exc}', file=sys.stderr)
        return 1
    if errors:
        print(f'FAIL: {len(errors)} structural error(s)')
        for err in errors:
            print(f' - {err}')
        return 1
    count = len(REQUIRED_DOCS) + len(CONTINUATION_DOCS) + 1
    print(f'PASS: {nr} requirements; {nt} acceptance scenarios; {nd} deferred decisions; 18 phases; {count} required files (21 original + continuation checkpoint).')
    print('Registry consistency only. Behavioral acceptance tests: NOT_RUN. Phases 2-18: NOT_STARTED.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
