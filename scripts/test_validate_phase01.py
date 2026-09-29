#!/usr/bin/env python3
"""Regression checks for the Phase 1 document validator, never trading tests.

Run: python scripts/test_validate_phase01.py
Each corruption is tested in an isolated temporary copy; source files are untouched.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_CASES = [
    ('duplicate requirement', 'requirements.json', lambda d: d['requirements'].append(d['requirements'][0].copy())),
    ('duplicate test', 'acceptance-tests.json', lambda d: d['acceptance_tests'].append(d['acceptance_tests'][0].copy())),
    ('missing requirement field', 'requirements.json', lambda d: d['requirements'][0].pop('normative_requirement')),
    ('invalid phase', 'requirements.json', lambda d: d['requirements'][0].update(primary_implementation_phase=19)),
    ('invalid requirement status', 'requirements.json', lambda d: d['requirements'][0].update(status='IMPLEMENTED')),
    ('dangling dependency', 'requirements.json', lambda d: d['requirements'][0].update(dependency_ids=['QNT-FR-9999'])),
    ('missing coverage', 'requirements.json', lambda d: d['requirements'][0].update(acceptance_test_ids=[])),
    ('orphan test', 'acceptance-tests.json', lambda d: d['acceptance_tests'][0].update(linked_requirement_ids=[])),
    ('requirement cycle', 'requirements.json', lambda d: d['requirements'][0].update(dependency_ids=['QNT-FR-0002'])),
    ('missing decision owner', 'requirements.json', lambda d: d['decisions'][0].pop('owner')),
    ('later phase PASS', 'requirements.json', lambda d: d['phases'][1].update(status='PASS')),
    ('fabricated trading PASS', 'acceptance-tests.json', lambda d: d['acceptance_tests'][0].update(execution_status='PASS')),
    ('phase cycle', 'requirements.json', lambda d: d['phases'][0].update(prerequisite_phases=[2])),
]
TEXT_CASES = [
    ('CSV mismatch', 'traceability.csv', lambda s: 'bad\nrow\n'),
    ('empty required file', 'README.md', lambda s: ''),
    ('malformed JSON', 'requirements.json', lambda s: '{'),
    ('acceptance oracle drift', 'acceptance-scenarios.md', lambda s: s.replace('Expected observable result:', 'Incorrect observable result:', 1)),
    ('decision owner drift', 'decisions-assumptions-and-open-questions.md', lambda s: s.replace('Owner: Frontend lead.', 'Owner: Unassigned.', 1)),
    ('readable phase PASS', 'phase-map-and-dependencies.md', lambda s: s.replace('| NOT_STARTED |', '| PASS |', 1)),
    ('missing document title', 'data-and-integration-contracts.md', lambda s: s.split('\n', 1)[1]),
    ('duplicate readable test', 'acceptance-scenarios.md', lambda s: s + '\n## QNT-AT-0001: Duplicate\n'),
    ('unknown prose ID', 'README.md', lambda s: s + '\nQNT-FR-9999\n'),
]


class ValidatorTests(unittest.TestCase):
    def run_validator(self, root):
        return subprocess.run(
            [sys.executable, str(ROOT / 'scripts/validate_phase01.py'), '--root', str(root)],
            cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace',
        )

    def test_valid_baseline(self):
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Behavioral acceptance tests: NOT_RUN', result.stdout)

    def test_rejects_corrupted_copies(self):
        rejected = 0
        with tempfile.TemporaryDirectory(prefix='quantora-phase01-regression-') as temp:
            target = Path(temp).resolve()
            # Cleanup is restricted to this newly allocated temporary directory.
            self.assertEqual(target.parent, Path(tempfile.gettempdir()).resolve())
            shutil.copytree(ROOT / 'docs/phase-01', target / 'docs/phase-01')
            (target / 'scripts').mkdir()
            shutil.copy2(ROOT / 'scripts/validate_phase01.py', target / 'scripts/validate_phase01.py')
            base = target / 'docs/phase-01'
            cases = [(label, name, mutate, True) for label, name, mutate in JSON_CASES]
            cases += [(label, name, mutate, False) for label, name, mutate in TEXT_CASES]
            for label, name, mutate, is_json in cases:
                with self.subTest(corruption=label):
                    path = base / name
                    original = path.read_bytes()
                    try:
                        if is_json:
                            data = json.loads(original.decode('utf-8'))
                            mutate(data)
                            changed = json.dumps(data)
                        else:
                            changed = mutate(original.decode('utf-8'))
                        self.assertNotEqual(changed.encode('utf-8'), original)
                        path.write_text(changed, encoding='utf-8')
                        result = self.run_validator(target)
                        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                        self.assertIn('FAIL:', result.stdout + result.stderr)
                        self.assertNotIn('Traceback', result.stdout + result.stderr)
                        rejected += 1
                    finally:
                        path.write_bytes(original)
            path = base / 'continuation-checkpoint.md'
            original = path.read_bytes()
            try:
                path.unlink()
                result = self.run_validator(target)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('Missing/empty required file', result.stdout)
                rejected += 1
            finally:
                path.write_bytes(original)
        self.assertEqual(rejected, len(JSON_CASES) + len(TEXT_CASES) + 1)
        print(f'Validator corruption fixtures: {rejected}/{len(JSON_CASES) + len(TEXT_CASES) + 1} rejected as expected.')


if __name__ == '__main__':
    unittest.main(verbosity=2)
