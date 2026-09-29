"""Real local foundation checks; reports dependency blockage separately from mocks.

Requires built core/web. Starts only owned child processes on unused loopback ports,
checks them, runs Playwright against those services, then requests graceful shutdown.
Exit 0 PASS, 1 FAIL, 2 BLOCKED. Does not start/reset Docker, databases or volumes.
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/phase-02/evidence'
OUT.mkdir(parents=True, exist_ok=True)
PYTHON = ROOT / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')
CORE = ROOT / ('services/trading-core/target/debug/quantora-core.exe' if os.name == 'nt'
               else 'services/trading-core/target/debug/quantora-core')
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(url, payload=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None,
                                 headers={'content-type': 'application/json'})
    try:
        response = OPENER.open(req, timeout=4)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, json.loads(response.read())


def free_port(port):
    with socket.socket() as sock:
        return sock.connect_ex(('127.0.0.1', port)) != 0


def main():
    result = {'checks': [], 'kind': 'real local processes; no dependency mocks', 'status': 'IN_PROGRESS'}
    processes = []
    preview = None
    handles = []
    env = dict(os.environ, QUANTORA_MODE='PAPER', PYTHONUNBUFFERED='1')
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0

    def record(name, status, detail):
        result['checks'].append({'name': name, 'status': status, 'detail': detail})
        print(f'{name}: {status}: {detail}', flush=True)

    try:
        occupied = [p for p in (8000, 8101, 4173) if not free_port(p)]
        if occupied:
            record('startup', 'BLOCKED', f'Existing listeners on {occupied}; not replaced or killed')
            return 2
        if not CORE.exists():
            record('startup', 'BLOCKED', 'Core binary missing; run cargo build --locked first')
            return 2
        for name, cmd, cwd in [
            ('core', [str(CORE)], ROOT),
            ('api', [str(PYTHON), '-m', 'quantora_api'], ROOT / 'services/control-api'),
        ]:
            handle = (OUT / f'{name}-runtime.log').open('w', encoding='utf-8')
            handles.append(handle)
            proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=handle, stderr=handle,
                                    creationflags=flags)
            processes.append((name, proc))
        for port in (8101, 8000):
            deadline = time.monotonic() + 15
            while True:
                try:
                    code, body = request(f'http://127.0.0.1:{port}/health/live')
                    if code == 200 and body['payload']['trading_enabled'] is False:
                        break
                except (OSError, ValueError):
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError(f'Service startup failed on port {port}')
                time.sleep(0.2)
        record('startup_liveness', 'PASS', 'Actual core and API respond on loopback; trading disabled')
        cases = json.loads((ROOT / 'contracts/fixtures.json').read_text())
        ping = next(c['value'] for c in cases if c['name'] == 'ping')
        code, reply = request('http://127.0.0.1:8000/api/v1/foundation/ping', ping)
        if code != 200 or reply['payload']['service'] != 'trading-core':
            raise RuntimeError('API-to-core bounded ping failed')
        record('api_core_contract', 'PASS', 'Actual HTTP API-to-Rust ping accepted; Rust envelope returned')
        code, health = request('http://127.0.0.1:8000/health/ready')
        deps = health['payload']['dependencies']
        result['dependency_status'] = deps
        if deps['core'] != 'UP':
            raise RuntimeError('Core readiness integration failed')
        record('real_dependencies', 'PASS' if code == 200 and all(v == 'UP' for v in deps.values()) else 'BLOCKED',
               json.dumps(deps) + '; Mongo requires writable quantora-rs primary, Redis requires PING')
        if code == 503:
            record('unavailable_dependency_readiness', 'PASS', 'Real missing dependencies cause NOT_READY/503; liveness stays 200')
        for name, cmd, cwd in [('core', [str(CORE)], ROOT),
                               ('api', [str(PYTHON), '-m', 'quantora_api'], ROOT / 'services/control-api')]:
            rejected = subprocess.run(cmd, cwd=cwd, env=dict(env, QUANTORA_MODE='LIVE'),
                                      capture_output=True, text=True, timeout=8)
            if rejected.returncode != 2 or 'invalid_configuration' not in rejected.stderr:
                raise RuntimeError(f'{name} LIVE startup was not rejected')
        record('live_configuration_rejection', 'PASS', 'Both real executables exit 2 on LIVE before binding')
        # Actual requests containing synthetic markers exercise output/log exclusion.
        for port in (8101, 8000):
            code, body = request(f'http://127.0.0.1:{port}/orders?api_key=SYNTHETIC_RUNTIME_SENTINEL',
                                 {'api_secret': 'SYNTHETIC_RUNTIME_SENTINEL'})
            if code != 404 or 'SYNTHETIC_RUNTIME_SENTINEL' in json.dumps(body):
                raise RuntimeError('Disabled route/redaction failed')
        # Own Vite directly. Playwright's Windows webServer process-tree teardown
        # can hang in the restricted host even after every browser test passes.
        preview_log = (OUT / 'preview.log').open('w', encoding='utf-8')
        handles.append(preview_log)
        preview = subprocess.Popen(['node', str(ROOT / 'node_modules/vite/bin/vite.js'),
                                    'preview', 'apps/web', '--host', '127.0.0.1',
                                    '--port', '4173', '--strictPort'], cwd=ROOT, env=env,
                                   stdout=preview_log, stderr=preview_log, creationflags=flags)
        deadline = time.monotonic() + 15
        while free_port(4173):
            if preview.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Owned preview failed to start')
            time.sleep(0.2)
        # File output preserves diagnostics even if the runner times out.
        with (OUT / 'browser.log').open('w', encoding='utf-8') as browser_log:
            browser = subprocess.run(['node', str(ROOT / 'node_modules/@playwright/test/cli.js'), 'test'],
                                     cwd=ROOT, env=dict(env, QUANTORA_EXTERNAL_PREVIEW='1'),
                                     stdout=browser_log, stderr=browser_log, timeout=120)
        record('browser', 'PASS' if browser.returncode == 0 else 'FAIL',
               'Playwright real-service chart/render/resize checks; see browser.log')
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        record('runtime_exception', 'FAIL', str(exc))
    finally:
        if preview is not None:
            if preview.poll() is None:
                preview.terminate()  # Only our ephemeral preview; no application state.
            preview.wait(timeout=5)
            record('preview_cleanup', 'PASS', 'Owned preview exited')
        for name, proc in reversed(processes):
            start = time.monotonic()
            try:
                if proc.poll() is None:
                    proc.send_signal(signal.CTRL_BREAK_EVENT if os.name == 'nt' else signal.SIGTERM)
                proc.wait(timeout=8)
                log = (OUT / f'{name}-runtime.log').read_text(encoding='utf-8')
                shutdown = any(json.loads(line).get('event') == 'shutdown'
                               for line in log.splitlines() if line.startswith('{'))
                if not shutdown:
                    raise RuntimeError('No graceful shutdown event')
                record(name + '_shutdown', 'PASS', f'Graceful event and process exit in {time.monotonic()-start:.3f}s; exit={proc.returncode}')
                record(name + '_redaction', 'PASS' if 'SYNTHETIC_RUNTIME_SENTINEL' not in log else 'FAIL',
                       'Actual request log excludes synthetic secret in URL/body')
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
                record(name + '_shutdown', 'FAIL', str(exc))
                if proc.poll() is None:
                    proc.kill()  # Only the child PID created above; never an existing listener.
                    proc.wait(timeout=5)
        for handle in handles:
            handle.close()
        statuses = [c['status'] for c in result['checks']]
        result['status'] = 'FAIL' if 'FAIL' in statuses else 'BLOCKED' if 'BLOCKED' in statuses else 'PASS'
        result['recorded_at_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        (OUT / 'runtime-latest.json').write_text(json.dumps(result, indent=2) + '\n')
    return {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[result['status']]


if __name__ == '__main__':
    sys.exit(main())
