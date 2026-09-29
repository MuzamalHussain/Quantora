"""Isolated browser-test control; refuses application/production databases. No public route."""
import asyncio
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/control-api'))
from quantora_api.config import Settings
from quantora_api.data import client
from quantora_api.market import migrate_market
from quantora_api.security import now


async def main():
    name = os.environ['QUANTORA_DATABASE']
    if not name.startswith('quantora_test_ui_') or os.getenv('QUANTORA_PHASE3_BROWSER') != '1':
        raise ValueError('Isolated test context required')
    mongo = client(Settings().mongo_url)
    try:
        user = await mongo[name].users.find_one({'email': sys.argv[2]})
        if not user:
            raise ValueError('Invalid test operation')
        if sys.argv[1] == 'expire':
            await mongo[name].sessions.update_many({'user_id': user['_id']},
                {'$set': {'expires_at': now()-timedelta(seconds=1)}})
        elif sys.argv[1] == 'seed-market' and os.getenv('QUANTORA_PHASE4_BROWSER') == '1':
            db = mongo[name]
            await migrate_market(db)
            await db.market_instruments.update_one({'venue':'BINANCE_USDM','symbol':'BTCUSDT'}, {'$set':
                {'venue':'BINANCE_USDM','symbol':'BTCUSDT','status':'TRADING','eligible':True,'tick_size':'0.10','step_size':'0.001','metadata_version':'browser-v1','stale':False}}, upsert=True)
            for interval, step in [('1m',60_000),('5m',300_000)]:
                current = int(time.time() * 1000) // step * step
                base = current - 11 * step
                for i in range(12):
                    key={'venue':'BINANCE_USDM','symbol':'BTCUSDT','interval':interval,'open_time_ms':base+i*step}
                    await db.market_candles.update_one(key, {'$set': {**key,'open':str(100+i),'high':str(101+i),'low':str(99+i),'close':str(100.5+i),'volume':str(10+i),'closed':True}}, upsert=True)
        else:
            raise ValueError('Invalid test operation')
    finally:
        await mongo.close()


if __name__ == '__main__':
    asyncio.run(main())
