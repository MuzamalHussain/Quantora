"""Required Phase 3 gate. Real DB/browser evidence; no existing data or keys replaced."""
import asyncio
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/phase-03/evidence'
STAMP = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
RUN = OUT / STAMP
PY = ROOT / '.venv/Scripts/python.exe'
sys.path.insert(0, str(ROOT / 'services/control-api'))
from quantora_api.config import Settings
from quantora_api.data import client, migrate


def record(result, name, status, **details):
    result['checks'].append(dict(name=name, status=status, **details))
    print(name+': '+status, flush=True)
    text = json.dumps(result, indent=2)+'\n'
    (RUN/'gate.json').write_text(text)
    (OUT/'gate-latest.json').write_text(text)


async def probe():
    mongo = client(Settings().mongo_url)
    try:
        hello = await mongo.admin.command('hello')
        return hello.get('isWritablePrimary') is True and hello.get('setName') == 'quantora-rs'
    finally:
        await mongo.close()


def main():
    RUN.mkdir(parents=True)
    result = {'status':'IN_PROGRESS','started_at_utc':STAMP,'checks':[]}
    # Phase 2 includes Phase 1 hashes/regressions, all language checks and real dependency checks.
    with (RUN/'phase02.log').open('w') as log:
        gate = subprocess.run([str(PY), 'scripts/verify_phase02.py'], cwd=ROOT, stdout=log, stderr=log, timeout=600)
    phase2 = json.loads((ROOT/'docs/phase-02/evidence/gate-latest.json').read_text())
    record(result, 'previous_phase_gate', phase2['status'], exit_code=gate.returncode,
           evidence='docs/phase-02/evidence/'+phase2['started_at_utc']+'/gate.json')
    try:
        available = asyncio.run(probe())
    except Exception:
        available = False
    if not available:
        record(result, 'phase03_integration', 'BLOCKED',
               detail='Actual MongoDB replica set/Redis unavailable; mocks not substituted')
        record(result, 'phase03_browser', 'BLOCKED', detail='Writable local quantora-rs primary unavailable')
    else:
        pytest_tmp = RUN/'pytest-tmp'
        pytest_tmp.mkdir()
        integration_env = dict(os.environ, TMP=str(pytest_tmp), TEMP=str(pytest_tmp))
        with (RUN/'phase03-integration.log').open('w') as log:
            integration = subprocess.run([str(PY), '-m', 'pytest', '-q', 'tests/test_saas.py'],
                                         cwd=ROOT/'services/control-api', env=integration_env,
                                         stdout=log, stderr=log,
                                         timeout=300)
        record(result, 'phase03_integration', 'PASS' if integration.returncode == 0 else 'FAIL',
               exit_code=integration.returncode, log=str((RUN/'phase03-integration.log').relative_to(ROOT)))
        name = 'quantora_test_ui_'+uuid4().hex
        mailbox = ROOT/'.cache'/('mail_'+uuid4().hex)
        env = dict(os.environ, QUANTORA_DATABASE=name, QUANTORA_PHASE3_BROWSER='1',
                   QUANTORA_CUSTODY_KEYS=json.dumps({'test':base64.b64encode(secrets.token_bytes(32)).decode()}),
                   QUANTORA_ACTIVE_KEY='test', QUANTORA_LOCAL_MAIL_DIR=str(mailbox))
        async def prepare():
            mongo = client(Settings().mongo_url)
            try:
                if await mongo[name].list_collection_names():
                    raise ValueError('Unexpected existing test database')
                await migrate(mongo[name])
            finally:
                await mongo.close()
        asyncio.run(prepare())
        try:
            # Run the proven owned-process harness in a subprocess with isolated test configuration.
            with (RUN/'browser-runtime.log').open('w') as log:
                runtime = subprocess.run([str(PY), 'scripts/verify_runtime.py'], cwd=ROOT, env=env,
                                         stdout=log, stderr=log, timeout=220)
            record(result, 'phase03_browser', 'PASS' if runtime.returncode == 0 else 'FAIL', exit_code=runtime.returncode)
            for filename in ('runtime-latest.json','browser.log','core-runtime.log','api-runtime.log'):
                shutil.copy2(ROOT/'docs/phase-02/evidence'/filename, RUN/filename)
        finally:
            async def cleanup():
                mongo = client(Settings().mongo_url)
                try:
                    await mongo.drop_database(name)  # Exact UUID database created above only.
                finally:
                    await mongo.close()
            asyncio.run(cleanup())
            # Encrypted test deliveries contain only ephemeral test tokens; leave files for inspection.
    expected = ['README','scope-and-traceability','authentication-and-sessions','tenant-isolation-and-roles',
                'data-model-and-indexes','migrations-and-idempotency','credential-encryption-and-rotation',
                'audit-and-retention','backup-and-restore','verification-matrix','sources','phase-03-report',
                'continuation-checkpoint']
    missing = [n for n in expected if not (ROOT/f'docs/phase-03/{n}.md').is_file()]
    registry = ROOT/'docs/phase-03/scope-evidence.json'
    if not registry.exists():
        missing.append('scope-evidence.json')
    registry_errors = []
    if registry.exists():
        scope = json.loads(registry.read_text())
        requirements = {r['id'] for r in json.loads((ROOT/'docs/phase-01/requirements.json').read_text())['requirements']}
        registry_errors += ['Unknown requirement '+rid for rid in scope['requirement_ids'] if rid not in requirements]
        registry_errors += ['Missing artifact '+item for item in scope['artifacts'] if not (ROOT/item).is_file()]
        if scope['full_requirement_completion'] is not False or scope['phase4_started'] is not False:
            registry_errors.append('Scope registry overclaims completion')
    record(result,'documentation','FAIL' if missing or registry_errors else 'PASS',
           missing=missing, registry_errors=registry_errors)
    statuses = [r['status'] for r in result['checks']]
    result['status'] = 'FAIL' if 'FAIL' in statuses else 'BLOCKED' if 'BLOCKED' in statuses else 'PASS'
    result['finished_at_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    (RUN/'gate.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'gate-latest.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Phase 3: '+result['status'])
    return {'PASS':0,'FAIL':1,'BLOCKED':2}[result['status']]


if __name__ == '__main__':
    sys.exit(main())
