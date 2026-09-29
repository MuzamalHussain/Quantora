"""Phase 4 gate: deterministic, real persistence, public provider, browser and regressions."""
import asyncio
import base64
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'docs/phase-04/evidence'
STAMP=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()); RUN=OUT/STAMP; PY=ROOT/'.venv/Scripts/python.exe'
sys.path.insert(0,str(ROOT/'services/control-api'))
from quantora_api.config import Settings
from quantora_api.data import client, migrate


def add(result,name,status,**detail):
    result['checks'].append({'name':name,'status':status,**detail}); print(f'{name}: {status}',flush=True)
    (RUN/'gate.json').write_text(json.dumps(result,indent=2)+'\n'); (OUT/'gate-latest.json').write_text(json.dumps(result,indent=2)+'\n')

def command(args,log,timeout=600,env=None,cwd=ROOT):
    with (RUN/log).open('w') as output:
        return subprocess.run(args,cwd=cwd,env=env,stdout=output,stderr=output,timeout=timeout,check=False).returncode

def main():
    RUN.mkdir(parents=True); result={'status':'IN_PROGRESS','started_at_utc':STAMP,'checks':[]}
    prior=command([str(PY),'scripts/verify_phase03.py'],'phase03.log')
    prior_gate=json.loads((ROOT/'docs/phase-03/evidence/gate-latest.json').read_text())
    add(result,'previous_phase_gate',prior_gate['status'],exit_code=prior)
    rust='''. ./scripts/rust-env.ps1; cargo fmt --manifest-path services/trading-core/Cargo.toml -- --check; if($LASTEXITCODE){exit $LASTEXITCODE}; cargo clippy --manifest-path services/trading-core/Cargo.toml --all-targets -- -D warnings; if($LASTEXITCODE){exit $LASTEXITCODE}; cargo test --manifest-path services/trading-core/Cargo.toml; if($LASTEXITCODE){exit $LASTEXITCODE}; cargo build --manifest-path services/trading-core/Cargo.toml --bin market_processor'''
    checks=[('rust_market',['powershell','-NoProfile','-Command',rust],'rust.log'),('python_quality',[str(PY),'-m','ruff','check','services/control-api/quantora_api','scripts/phase04_live_smoke.py','scripts/phase04_collector.py'],'python-quality.log'),('python_types',[str(PY),'-m','mypy','--config-file','services/control-api/pyproject.toml','services/control-api/quantora_api'],'python-types.log'),('web_build',['npm.cmd','--workspace','apps/web','run','build'],'web-build.log')]
    for name,args,log in checks:
        code=command(args,log); add(result,name,'PASS' if code==0 else 'FAIL',exit_code=code)
    temp=RUN/'pytest-tmp'; temp.mkdir(); env=dict(os.environ,TMP=str(temp),TEMP=str(temp))
    code=command([str(PY),'-m','pytest','-q','tests/test_saas.py'], 'integration.log',300,env,ROOT/'services/control-api')
    add(result,'market_integration','PASS' if code==0 else 'FAIL',exit_code=code)
    rest=OUT/'live-smoke.json'; ws=OUT/'live-websocket.json'
    rest_data=json.loads(rest.read_text()) if rest.exists() else {}
    rest_ok=bool(rest_data.get('discovery',{}).get('eligible_count') and rest_data.get('funding',{}).get('settled_records') and rest_data.get('premium',{}).get('mark_present'))
    ws_data=json.loads(ws.read_text()) if ws.exists() else {}
    ws_ok=ws_data.get('result')=='PASS' and any(e.get('type')=='data' for e in ws_data.get('events',[]))
    add(result,'public_rest','PASS' if rest_ok else 'BLOCKED',evidence=str(rest.relative_to(ROOT)) if rest_ok else None)
    add(result,'public_websocket','PASS' if ws_ok else 'BLOCKED',evidence=str(ws.relative_to(ROOT)) if ws_ok else None)
    name='quantora_test_ui_'+uuid4().hex; mailbox=ROOT/'.cache'/('mail_'+uuid4().hex)
    browser_env=dict(os.environ,QUANTORA_DATABASE=name,QUANTORA_PHASE3_BROWSER='1',QUANTORA_PHASE4_BROWSER='1',QUANTORA_PHASE4_LIVE_DB='1',QUANTORA_PHASE4_BROWSER_EVIDENCE=str(RUN/'live-chart.json'),QUANTORA_CUSTODY_KEYS=json.dumps({'test':base64.b64encode(secrets.token_bytes(32)).decode()}),QUANTORA_ACTIVE_KEY='test',QUANTORA_LOCAL_MAIL_DIR=str(mailbox))
    async def prepare(drop=False):
        mongo=client(Settings().mongo_url)
        try:
            if drop: await mongo.drop_database(name)
            else: await migrate(mongo[name])
        finally: await mongo.close()
    try:
        asyncio.run(prepare())
        start_ms=int(time.time()*1000)-3_600_000
        collector_code=command([str(PY),'scripts/phase04_collector.py','--database',name,'--symbol','BTCUSDT','--seconds','15','--start-ms',str(start_ms)],'collector.log',180,browser_env)
        try: collector_data=json.loads((RUN/'collector.log').read_text().strip().splitlines()[-1])
        except (ValueError,IndexError): collector_data={}
        counts=collector_data.get('stream_counts',{})
        polls=collector_data.get('poll_counts',{})
        collector_ok=collector_code==0 and all(counts.get(k,0)>0 for k in ('kline','mark','trade','depth')) and polls.get('open_interest')==1 and polls.get('settled_funding',0)>0
        add(result,'live_collector','PASS' if collector_ok else 'FAIL',exit_code=collector_code,evidence='collector.log',counts=counts,polls=polls)
        async def inspect_storage():
            mongo=client(Settings().mongo_url)
            try:
                db=mongo[name]
                book=await db.market_observations.find_one({'venue':'BINANCE_USDM','symbol':'BTCUSDT','kind':'BOOK'})
                state=await db.market_quality.find_one({'venue':'BINANCE_USDM','symbol':'BTCUSDT','channel':'STREAM'},sort=[('recorded_at',-1)])
                return {'instrument_count':await db.market_instruments.count_documents({'eligible':True}),
                        'candle_intervals':{i:await db.market_candles.count_documents({'symbol':'BTCUSDT','interval':i}) for i in ('1m','5m','15m')},
                        'open_interest_count':await db.market_observations.count_documents({'symbol':'BTCUSDT','kind':'OPEN_INTEREST'}),
                        'funding_count':await db.market_observations.count_documents({'symbol':'BTCUSDT','kind':'SETTLED_FUNDING'}),
                        'book_valid':bool(book and book.get('valid')),'book_last_update_id':book.get('last_update_id') if book else None,
                        'book_best_bid':book.get('best_bid') if book else None,'book_best_ask':book.get('best_ask') if book else None,
                        'stream_terminal_state':state.get('state') if state else None,
                        'raw_diagnostic_count':await db.market_raw_events.count_documents({'kind':'PUBLIC_DIAGNOSTIC'}),
                        'backfill_checkpoints':{i:bool(await db.market_checkpoints.find_one({'_id':f'backfill:BTCUSDT:{i}'})) for i in ('1m','5m','15m')}}
            finally: await mongo.close()
        storage=asyncio.run(inspect_storage())
        (RUN/'collector-storage.json').write_text(json.dumps(storage,indent=2)+'\n')
        storage_ok=storage['instrument_count']>0 and all(storage['candle_intervals'].values()) and storage['open_interest_count']>0 and storage['funding_count']>0 and storage['book_valid'] and storage['book_last_update_id'] and storage['book_best_bid'] and storage['book_best_ask'] and storage['stream_terminal_state']=='DISCONNECTED' and 0<storage['raw_diagnostic_count']<=64 and all(storage['backfill_checkpoints'].values())
        add(result,'live_storage','PASS' if storage_ok else 'FAIL',evidence='collector-storage.json')
        code=command([str(PY),'scripts/verify_runtime.py'],'browser-runtime.log',240,browser_env)
        add(result,'browser','PASS' if code==0 else 'FAIL',exit_code=code)
        chart_path=RUN/'live-chart.json'
        try: chart=json.loads(chart_path.read_text())
        except (OSError,ValueError): chart={}
        chart_ok=chart.get('source')=='BINANCE_WS' and chart.get('chart_visible') is True and chart.get('collector_fence',0)>collector_data.get('fence',0) and chart.get('after_received_at_ms',0)>chart.get('before_received_at_ms',0)
        add(result,'live_chart_update','PASS' if chart_ok else 'FAIL',evidence='live-chart.json' if chart_ok else None)
        for f in ('browser.log','api-runtime.log','core-runtime.log','runtime-latest.json'):
            if (ROOT/'docs/phase-02/evidence'/f).exists(): shutil.copy2(ROOT/'docs/phase-02/evidence'/f,RUN/f)
    finally: asyncio.run(prepare(True))
    expected=['README','scope-and-traceability','binance-endpoints-and-sources','instrument-discovery','ingestion-and-storage','order-book-synchronization','rate-limits-and-recovery','data-quality-and-freshness','read-api-and-ui','verification-matrix','phase-04-report','continuation-checkpoint']
    missing=[x for x in expected if not (ROOT/f'docs/phase-04/{x}.md').exists()]
    if not (ROOT/'docs/phase-04/scope-evidence.json').exists(): missing.append('scope-evidence.json')
    add(result,'documentation','PASS' if not missing else 'FAIL',missing=missing)
    states=[x['status'] for x in result['checks']]; result['status']='FAIL' if 'FAIL' in states else 'BLOCKED' if 'BLOCKED' in states else 'PASS'; result['finished_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    (RUN/'gate.json').write_text(json.dumps(result,indent=2)+'\n'); (OUT/'gate-latest.json').write_text(json.dumps(result,indent=2)+'\n'); print('Phase 4: '+result['status']); return {'PASS':0,'FAIL':1,'BLOCKED':2}[result['status']]
if __name__=='__main__': sys.exit(main())
