"""Focused isolated Phase 4 browser check; owns and drops only its UUID database."""
import asyncio
import base64
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]; PY=ROOT/'.venv/Scripts/python.exe'
sys.path.insert(0,str(ROOT/'services/control-api'))
from quantora_api.config import Settings
from quantora_api.data import client, migrate

name='quantora_test_ui_'+uuid4().hex
env=dict(os.environ,QUANTORA_DATABASE=name,QUANTORA_PHASE3_BROWSER='1',QUANTORA_PHASE4_BROWSER='1',QUANTORA_CUSTODY_KEYS=json.dumps({'test':base64.b64encode(secrets.token_bytes(32)).decode()}),QUANTORA_ACTIVE_KEY='test',QUANTORA_LOCAL_MAIL_DIR=str(ROOT/'.cache'/('mail_'+uuid4().hex)))
async def database(drop=False):
    mongo=client(Settings().mongo_url)
    try:
        if drop: await mongo.drop_database(name)
        else: await migrate(mongo[name])
    finally: await mongo.close()
asyncio.run(database())
try:
    result=subprocess.run([str(PY),'scripts/verify_runtime.py'],cwd=ROOT,env=env,check=False)
finally:
    asyncio.run(database(True))
sys.exit(result.returncode)
