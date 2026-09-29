"""Phase 2 verification, without installing dependencies or resetting services.

Run from any directory with Python 3.12. Exit: 0 PASS, 1 FAIL, 2 BLOCKED.
Preserves command logs in timestamped directories; no mock substitutes for runtime.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/phase-02/evidence'
STAMP = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
RUN = OUT / STAMP
PY = ROOT / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')
ENV = dict(os.environ, CARGO_HOME=str(ROOT / '.tools/cargo'),
           RUSTUP_HOME=str(ROOT / '.tools/rustup'))
ENV['PATH'] = str(ROOT / '.tools/cargo/bin') + os.pathsep + ENV['PATH']
RESULT = {'started_at_utc': STAMP, 'checks': [], 'status': 'IN_PROGRESS'}


def save():
    text = json.dumps(RESULT, indent=2) + '\n'
    (RUN / 'gate.json').write_text(text, encoding='utf-8')
    (OUT / 'gate-latest.json').write_text(text, encoding='utf-8')


def record(name, status, **kwargs):
    RESULT['checks'].append(dict(name=name, status=status, **kwargs))
    print(f'{name}: {status}', flush=True)
    save()


def command(name, args, cwd=ROOT, timeout=240, blocked_exit=False):
    start = time.monotonic()
    log = RUN / (name + '.log')
    try:
        with log.open('w', encoding='utf-8') as output:
            p = subprocess.run([str(a) for a in args], cwd=cwd, env=ENV,
                               stdout=output, stderr=output, timeout=timeout)
        status = 'PASS' if p.returncode == 0 else 'BLOCKED' if blocked_exit and p.returncode == 2 else 'FAIL'
        record(name, status, command=[str(a) for a in args], cwd=str(cwd),
               exit_code=p.returncode, duration_seconds=round(time.monotonic()-start, 3),
               log=log.relative_to(ROOT).as_posix())
    except (OSError, subprocess.TimeoutExpired) as exc:
        record(name, 'BLOCKED' if isinstance(exc, FileNotFoundError) else 'FAIL',
               command=[str(a) for a in args], detail=str(exc), log=log.relative_to(ROOT).as_posix())


def main():
    RUN.mkdir(parents=True, exist_ok=False)
    baseline = json.loads((ROOT / 'docs/phase-02/baseline-hashes.json').read_text())
    changed = [p for p, digest in baseline.items() if not (ROOT / p).is_file()
               or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
    record('baseline_hashes', 'FAIL' if changed else 'PASS', files=len(baseline), changed=changed)
    command('phase01', [PY, ROOT / 'scripts/validate_phase01.py'])
    command('phase01_regression', [PY, ROOT / 'scripts/test_validate_phase01.py'])
    cargo = shutil.which('cargo', path=ENV['PATH']) or 'cargo'
    rust = ROOT / 'services/trading-core'
    for name, args in [('rust_fmt', ['fmt', '--check']), ('rust_build', ['build', '--locked']),
                       ('rust_clippy', ['clippy', '--locked', '--all-targets', '--', '-D', 'warnings']),
                       ('rust_tests', ['test', '--locked'])]:
        command(name, [cargo, *args], rust)
    api = ROOT / 'services/control-api'
    # Phase-scoped regression: later-phase suites have their own real dependency gates.
    for name, args in [('python_lint', ['ruff', 'check', '.']), ('python_types', ['mypy']),
                       ('python_tests', ['pytest', '-q', 'tests/test_foundation.py'])]:
        command(name, [PY, '-m', *args], api)
    node = shutil.which('node') or 'node'
    command('generated_contracts', [node, ROOT / 'scripts/generate-contracts.mjs', '--check'])
    # Calling npm's JS entry directly avoids shell quoting and inherited cmd pipes.
    npm = Path(node).parent / 'node_modules/npm/bin/npm-cli.js'
    for name, task in [('web_build', 'build'), ('web_tests', 'test')]:
        command(name, [node, npm, 'run', task, '--workspace', 'apps/web'])
    docker = shutil.which('docker')
    if docker:
        command('compose_config', [docker, 'compose', '-f', ROOT / 'infra/compose.yaml', 'config', '--quiet'])
    else:
        record('compose_config', 'BLOCKED', detail='Docker executable absent; Compose not interpreted or started')
    command('runtime', [PY, ROOT / 'scripts/verify_runtime.py'], timeout=200, blocked_exit=True)
    for name in ['runtime-latest.json', 'browser.log', 'preview.log', 'core-runtime.log', 'api-runtime.log']:
        if (OUT / name).exists():
            shutil.copy2(OUT / name, RUN / name)
    required = ['README', 'architecture', 'service-and-data-boundaries', 'decision-resolutions',
                'dependency-and-version-register', 'chart-engine-evaluation', 'contracts-and-versioning',
                'configuration-and-secrets', 'local-development', 'recovery-and-observability',
                'verification-matrix', 'sources', 'phase-02-report', 'continuation-checkpoint']
    errors = [f'Missing/empty document {name}' for name in required
              if not (ROOT / f'docs/phase-02/{name}.md').is_file()
              or (ROOT / f'docs/phase-02/{name}.md').stat().st_size < 100]
    registry = json.loads((ROOT / 'docs/phase-02/scope-evidence.json').read_text())
    ids = {r['id'] for r in json.loads((ROOT / 'docs/phase-01/requirements.json').read_text())['requirements']}
    for item in registry['items']:
        errors.extend(f"Unknown requirement {rid}" for rid in item['requirement_ids'] if rid not in ids)
        errors.extend(f'Missing artifact {path}' for path in item['artifacts'] if not (ROOT / path).is_file())
        if item['full_requirement_completion'] is not False:
            errors.append('Foundation evidence must not claim full trading acceptance')
    record('documentation', 'FAIL' if errors else 'PASS', errors=errors,
           detail='File/ID/reference integrity only; semantic review is separately recorded in report')
    states = [c['status'] for c in RESULT['checks']]
    RESULT['status'] = 'FAIL' if 'FAIL' in states else 'BLOCKED' if 'BLOCKED' in states else 'PASS'
    RESULT['finished_at_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    # Fingerprints bind the results to tested implementation and locked dependencies.
    paths = list(ROOT.glob('contracts/*')) + list(ROOT.glob('scripts/*'))
    paths += list((ROOT / 'services/control-api/quantora_api').glob('*.py'))
    paths += list((ROOT / 'services/control-api/tests').glob('*.py'))
    paths += list((ROOT / 'services/trading-core/src').glob('*.rs'))
    paths += list((ROOT / 'apps/web/src').glob('*')) + list((ROOT / 'tests/browser').glob('*'))
    paths += [ROOT / p for p in ['package.json', 'package-lock.json', 'playwright.config.ts',
              'rust-toolchain.toml', 'services/trading-core/Cargo.toml', 'services/trading-core/Cargo.lock',
              'services/control-api/requirements.lock', 'services/control-api/pyproject.toml',
              'apps/web/package.json', 'apps/web/vite.config.ts', 'infra/compose.yaml', 'infra/init-replica.js']]
    RESULT['file_hashes'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in paths if p.is_file()}
    save()
    print('Phase 2: ' + RESULT['status'], flush=True)
    return {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[RESULT['status']]


if __name__ == '__main__':
    sys.exit(main())
