"""Bounded shared Binance public collector; no credential or mutation capability."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from pymongo import AsyncMongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError
from pymongo.write_concern import WriteConcern

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/control-api"))
REST = "https://fapi.binance.com"
VENUE = "BINANCE_USDM"
QUEUE_LIMIT = 2048


class LeaseLost(RuntimeError): pass


class MarketProcessor:
    """Rust owns provider normalization and sequence-aware book state."""
    def __init__(self, process: asyncio.subprocess.Process) -> None:
        self.process=process
        self.lock=asyncio.Lock()

    @classmethod
    async def start(cls)->MarketProcessor:
        binary=ROOT/"services/trading-core/target/debug/market_processor.exe"
        if not binary.exists(): raise RuntimeError("build the Rust market_processor binary first")
        process=await asyncio.create_subprocess_exec(str(binary),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        return cls(process)

    async def call(self,op:str,value:dict[str,Any],epoch:int=0)->dict[str,Any]:
        if not self.process.stdin or not self.process.stdout: raise RuntimeError("market processor pipe unavailable")
        async with self.lock:
            self.process.stdin.write((json.dumps({"op":op,"value":value,"epoch":epoch},separators=(",",":"))+"\n").encode())
            await self.process.stdin.drain()
            line=await asyncio.wait_for(self.process.stdout.readline(),5)
        if not line: raise RuntimeError("Rust market processor stopped")
        result=json.loads(line)
        if not result.get("ok"): raise ValueError("market normalization rejected: "+str(result.get("error")))
        return result

    async def close(self)->None:
        if self.process.stdin: self.process.stdin.close()
        await asyncio.wait_for(self.process.wait(),5)


class RequestBudget:
    """One bounded IP-weight budget for this single-owner collector process."""
    def __init__(self, db: Any) -> None:
        self.db=db; self.lock=asyncio.Lock(); self.window=time.monotonic(); self.used=0

    async def reserve(self,path:str)->None:
        weight={"/fapi/v1/depth":20,"/fapi/v1/klines":10}.get(path,1)
        async with self.lock:
            cooldown=await self.db.market_checkpoints.find_one({"_id":"rate:binance-usdm"})
            until=cooldown.get("cooldown_until") if cooldown else None
            if until and until>datetime.now(UTC):
                await asyncio.sleep((until-datetime.now(UTC)).total_seconds())
            elapsed=time.monotonic()-self.window
            if elapsed>=60: self.window=time.monotonic(); self.used=0
            if self.used+weight>1000:
                await asyncio.sleep(max(0,60-elapsed)); self.window=time.monotonic(); self.used=0
            self.used+=weight

    async def observe(self,response:httpx.Response)->None:
        header=response.headers.get("x-mbx-used-weight-1m")
        if header and header.isdigit(): self.used=max(self.used,int(header))

    async def cooldown(self,seconds:int)->None:
        until=datetime.now(UTC)+timedelta(seconds=seconds)
        await self.db.market_checkpoints.update_one({"_id":"rate:binance-usdm"},{"$set":{"channel":"RATE","symbol":"*","interval":"1m","cooldown_until":until,"updated_at":datetime.now(UTC)}},upsert=True)


class Store:
    def __init__(self, db: Any, owner: str) -> None:
        self.db, self.owner, self.fence = db, owner, 0
        self.continuous = False
        self.budget=RequestBudget(db)
        self.processor:MarketProcessor|None=None

    async def normalize(self,op:str,value:dict[str,Any],epoch:int=0)->dict[str,Any]:
        if not self.processor: raise RuntimeError("Rust market processor is required")
        return await self.processor.call(op,value,epoch)

    async def mutate(self,collection:str,method:str,*args:Any,**kwargs:Any)->Any:
        """Serialize ownership check and durable write in one replica-set transaction."""
        async def action(session:Any)->Any:
            lease=await self.db.market_checkpoints.find_one_and_update(
                {"_id":"collector:binance-usdm","owner":self.owner,"fence":self.fence,"lease_until":{"$gt":datetime.now(UTC)}},
                {"$inc":{"write_seq":1}},session=session,return_document=ReturnDocument.AFTER)
            if not lease: raise LeaseLost("collector lease lost before write")
            return await getattr(self.db[collection],method)(*args,session=session,**kwargs)
        async with self.db.client.start_session() as session:
            return await session.with_transaction(action,write_concern=WriteConcern("majority",j=True),max_commit_time_ms=3000)
    async def acquire(self, seconds: int = 30) -> None:
        now=datetime.now(UTC)
        try:
            lease=await self.db.market_checkpoints.find_one_and_update(
                {"_id":"collector:binance-usdm","$or":[{"lease_until":{"$lt":now}},{"owner":self.owner},{"owner":{"$exists":False}}]},
                {"$set":{"channel":"LEASE","symbol":"*","interval":"*","owner":self.owner,"lease_until":now+timedelta(seconds=seconds),"updated_at":now},"$inc":{"fence":1}},
                upsert=True,return_document=ReturnDocument.AFTER)
        except DuplicateKeyError as exc:
            raise LeaseLost("collector lease held") from exc
        if not lease: raise LeaseLost("collector lease held")
        self.fence=int(lease["fence"])
    async def renew(self, seconds: int = 30) -> None:
        result=await self.db.market_checkpoints.update_one({"_id":"collector:binance-usdm","owner":self.owner,"fence":self.fence},{"$set":{"lease_until":datetime.now(UTC)+timedelta(seconds=seconds)}})
        if result.modified_count != 1: raise LeaseLost("collector lease lost")
    async def release(self) -> None:
        await self.db.market_checkpoints.update_one({"_id":"collector:binance-usdm","owner":self.owner,"fence":self.fence},{"$set":{"lease_until":datetime.now(UTC),"owner":None}})
    async def quality(self,symbol:str,channel:str,state:str,source_ms:int|None=None,detail:str="") -> None:
        await self.mutate("market_quality","insert_one",{"venue":VENUE,"symbol":symbol,"channel":channel,"state":state,"source_time_ms":source_ms,"received_at_ms":int(time.time()*1000),"recorded_at":datetime.now(UTC),"fence":self.fence,"detail":detail[:120]})


async def request(store:Store,http:httpx.AsyncClient,path:str,params:dict[str,Any]|None=None)->Any:
    attempt=0
    while store.continuous or attempt<4:
        await store.budget.reserve(path)
        try:
            response=await http.get(REST+path,params=params)
        except httpx.RequestError:
            if not store.continuous and attempt == 3: raise
            await asyncio.sleep(min(.2*(2**min(attempt,7))+random.random()*.1,30))
            attempt+=1
            continue
        await store.budget.observe(response)
        if response.status_code in (418,429):
            delay=max(1,int(response.headers.get("Retry-After","120" if response.status_code==418 else "1")))
            await store.budget.cooldown(delay)
            if response.status_code==418: raise RuntimeError(f"provider ban; retry after {delay}s")
            await asyncio.sleep(delay)
            attempt+=1
            continue
        if response.status_code>=500:
            await asyncio.sleep(min(.2*(2**min(attempt,7))+random.random()*.1,30))
            attempt+=1
            continue
        response.raise_for_status(); return response.json()
    raise RuntimeError("bounded provider retries exhausted")


async def discover(store:Store,http:httpx.AsyncClient)->list[str]:
    try:
        data=await request(store,http,"/fapi/v1/exchangeInfo")
    except (httpx.HTTPError,RuntimeError):
        await store.mutate("market_instruments","update_many",{"venue":VENUE},{"$set":{"stale":True,"updated_at":datetime.now(UTC)}})
        await store.quality("*","DISCOVERY","STALE",detail="provider discovery unavailable; prior universe retained")
        raise
    seen=[]; effective=int(time.time()*1000)
    for value in data["symbols"]:
        filters={x["filterType"]:x for x in value.get("filters",[]) if "filterType" in x}
        price_filter=filters.get("PRICE_FILTER",{})
        lot_filter=filters.get("LOT_SIZE",{})
        normalized=await store.normalize("instrument",value)
        doc={"venue":VENUE,"symbol":normalized["symbol"],"pair":value.get("pair"),"base_asset":value.get("baseAsset"),"quote_asset":value.get("quoteAsset"),"margin_asset":value.get("marginAsset"),"contract_type":value.get("contractType"),"status":normalized["status"],"eligible":normalized["eligible"],"tick_size":normalized["tick_size"],"min_price":price_filter.get("minPrice"),"max_price":price_filter.get("maxPrice"),"step_size":normalized["step_size"],"min_qty":lot_filter.get("minQty"),"max_qty":lot_filter.get("maxQty"),"onboard_time_ms":normalized["onboard_time_ms"],"metadata_version":hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest(),"stale":False,"updated_at":datetime.now(UTC)}
        old=await store.db.market_instruments.find_one({"venue":VENUE,"symbol":doc["symbol"]},{"metadata_version":1,"stale":1})
        if not old or old.get("metadata_version")!=doc["metadata_version"] or old.get("stale"):
            await store.mutate("market_instruments","update_one",{"venue":VENUE,"symbol":doc["symbol"]},{"$set":doc},upsert=True)
            await store.mutate("market_instrument_versions","update_one",{"venue":VENUE,"symbol":doc["symbol"],"metadata_version":doc["metadata_version"]},{"$setOnInsert":{**doc,"effective_at_ms":effective}},upsert=True)
        if doc["eligible"]: seen.append(doc["symbol"])
    await store.mutate("market_instruments","update_many",{"venue":VENUE,"symbol":{"$nin":[x["symbol"] for x in data["symbols"]]}},{"$set":{"stale":True,"eligible":False,"updated_at":datetime.now(UTC)}})
    await store.quality("*","DISCOVERY","LIVE",effective,f"eligible={len(seen)}"); return seen


async def save_candle(store:Store,doc:dict[str,Any])->None:
    key={"venue":VENUE,"symbol":doc["symbol"],"interval":doc["interval"],"open_time_ms":doc["open_time_ms"]}
    old=await store.db.market_candles.find_one(key)
    fields=("open","high","low","close","volume")
    if old and old.get("closed") and any(old.get(x)!=doc[x] for x in fields):
        await store.mutate("market_raw_events","insert_one",{"venue":VENUE,"symbol":doc["symbol"],"kind":"CANDLE_CORRECTION","interval":doc["interval"],"open_time_ms":doc["open_time_ms"],"previous":{x:old.get(x) for x in fields},"corrected":{x:doc[x] for x in fields},"recorded_at":datetime.now(UTC),"expire_at":datetime.now(UTC)+timedelta(days=7)})
        await store.quality(doc["symbol"],"CANDLE","CORRECTED",doc["open_time_ms"])
    if not old or not old.get("closed") or any(old.get(x)!=doc[x] for x in fields):
        await store.mutate("market_candles","update_one",key,{"$set":doc},upsert=True)


async def backfill(store:Store,http:httpx.AsyncClient,symbol:str,interval:str,start_ms:int,end_ms:int)->int:
    step={"1m":60_000,"5m":300_000,"15m":900_000}[interval]
    checkpoint_id=f"backfill:{symbol}:{interval}"
    old=await store.db.market_checkpoints.find_one({"_id":checkpoint_id})
    saved=int(old.get("next_ms",start_ms)) if old else start_ms
    cursor=max(start_ms,min(saved,end_ms-step))
    total=0
    while cursor<end_ms:
        rows=await request(store,http,"/fapi/v1/klines",{"symbol":symbol,"interval":interval,"startTime":cursor,"endTime":min(end_ms,cursor+200*86_400_000),"limit":1500})
        if not rows: break
        previous_open=None
        for row in rows:
            doc={"venue":VENUE,"symbol":symbol,"interval":interval,"open_time_ms":row[0],"close_time_ms":row[6],"open":row[1],"high":row[2],"low":row[3],"close":row[4],"volume":row[5],"closed":row[6]<int(time.time()*1000),"source":"BINANCE_REST","received_at_ms":int(time.time()*1000)}
            if previous_open is not None and row[0]-previous_open>step:
                await store.quality(symbol,"CANDLE","GAP",row[0],f"{interval}: missing intervals after {previous_open}; cause unknown")
            previous_open=int(row[0])
            await save_candle(store,doc); total+=1
        last=rows[-1]
        cursor=int(last[6])+1 if int(last[6])<int(time.time()*1000) else int(last[0])
        await store.mutate("market_checkpoints","update_one",{"_id":checkpoint_id},{"$set":{"channel":"BACKFILL","symbol":symbol,"interval":interval,"next_ms":cursor,"updated_at":datetime.now(UTC),"fence":store.fence}},upsert=True)
        if len(rows)<1500 or cursor<=int(last[0]): break
    return total


async def poll_oi_funding(store:Store,http:httpx.AsyncClient,symbol:str,include_funding:bool=True)->dict[str,int]:
    oi=await request(store,http,"/fapi/v1/openInterest",{"symbol":symbol})
    if oi.get("symbol")!=symbol or not oi.get("openInterest") or not isinstance(oi.get("time"),int):
        raise RuntimeError("invalid open-interest response")
    now_ms=int(time.time()*1000)
    await store.mutate("market_observations","update_one",
        {"venue":VENUE,"symbol":symbol,"kind":"OPEN_INTEREST","source_time_ms":oi["time"]},
        {"$setOnInsert":{"venue":VENUE,"symbol":symbol,"kind":"OPEN_INTEREST","source_time_ms":oi["time"],"received_at_ms":now_ms,"open_interest":oi["openInterest"],"fence":store.fence}},upsert=True)
    count=0
    if include_funding:
        funding=await request(store,http,"/fapi/v1/fundingRate",{"symbol":symbol,"limit":2})
        for row in funding:
            if row.get("symbol")!=symbol or not isinstance(row.get("fundingTime"),int) or not row.get("fundingRate"):
                raise RuntimeError("invalid settled-funding response")
            await store.mutate("market_observations","update_one",
                {"venue":VENUE,"symbol":symbol,"kind":"SETTLED_FUNDING","source_time_ms":row["fundingTime"]},
                {"$setOnInsert":{"venue":VENUE,"symbol":symbol,"kind":"SETTLED_FUNDING","source_time_ms":row["fundingTime"],"received_at_ms":now_ms,"funding_rate":row["fundingRate"],"semantics":"SETTLED","fence":store.fence}},upsert=True)
            count+=1
    await store.quality(symbol,"REST_POLL","LIVE",oi["time"],f"open_interest=1,settled_funding={count}")
    return {"open_interest":1,"settled_funding":count}


async def stream(store:Store,http:httpx.AsyncClient,symbol:str,seconds:int)->dict[str,int]:
    env=dict(os.environ,QUANTORA_MARKET_SYMBOL=symbol,QUANTORA_COLLECTOR_SECONDS=str(seconds)); process=await asyncio.create_subprocess_exec("node","scripts/phase04-stream.mjs",cwd=ROOT,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    assert process.stdout and process.stderr
    queue:asyncio.Queue[dict[str,Any]]=asyncio.Queue(QUEUE_LIMIT); counts={"kline":0,"mark":0,"trade":0,"depth":0}; valid=False; epoch=0; acked:set[str]=set(); signaled_live=False; captured=0
    async def receive()->None:
        async for raw in process.stdout:
            item=json.loads(raw); value=item["value"]
            if "error" in value: raise RuntimeError("provider subscription rejected")
            if "id" in value:
                expected=1 if item["route"]=="market" else 2
                if value.get("result") is not None or value["id"]!=expected: raise RuntimeError("unexpected provider subscription acknowledgement")
                acked.add(item["route"])
                continue
            if item["route"] not in acked: raise RuntimeError("public data arrived before subscription acknowledgement")
            try: queue.put_nowait(item)
            except asyncio.QueueFull:
                await store.quality(symbol,"STREAM","INVALID",detail="queue overflow"); raise RuntimeError("bounded queue overflow")
    receiver=asyncio.create_task(receive())
    snapshot=None
    try:
        deadline=time.monotonic()+seconds+5
        next_oi=time.monotonic()+60
        next_funding=time.monotonic()+300
        while time.monotonic()<deadline:
            if receiver.done() and receiver.exception(): raise receiver.exception()
            if time.monotonic()>=next_oi:
                include_funding=time.monotonic()>=next_funding
                try: await poll_oi_funding(store,http,symbol,include_funding)
                except (httpx.HTTPError,RuntimeError) as exc:
                    await store.quality(symbol,"REST_POLL","DEGRADED",detail=type(exc).__name__)
                next_oi=time.monotonic()+60
                if include_funding: next_funding=time.monotonic()+300
            try: item=await asyncio.wait_for(queue.get(),1)
            except TimeoutError:
                if process.returncode is not None and queue.empty(): break
                continue
            if receiver.done() and receiver.exception(): raise receiver.exception()
            value=item["value"]; kind=value.get("e"); now_ms=item["received_at_ms"]
            if captured<64 and (kind!="depthUpdate" or counts["depth"]%100==0):
                await store.mutate("market_raw_events","insert_one",{"venue":VENUE,"symbol":symbol,"kind":"PUBLIC_DIAGNOSTIC","event_type":kind or "UNKNOWN","payload":value,"received_at_ms":now_ms,"recorded_at":datetime.now(UTC),"expire_at":datetime.now(UTC)+timedelta(days=1),"fence":store.fence})
                captured+=1
            if kind=="depthUpdate":
                counts["depth"]+=1
                if snapshot is None:
                    snapshot=await request(store,http,"/fapi/v1/depth",{"symbol":symbol,"limit":1000})
                    epoch+=1
                    await store.normalize("book_snapshot",snapshot,epoch)
                try:
                    state=await store.normalize("book_delta",value,epoch)
                except ValueError as exc:
                    valid=False; snapshot=None
                    await store.mutate("market_observations","update_one",{"venue":VENUE,"symbol":symbol,"kind":"BOOK"},{"$set":{"valid":False,"source_time_ms":value.get("E"),"received_at_ms":now_ms,"fence":store.fence}})
                    await store.quality(symbol,"DEPTH","INVALID",value.get("E"),str(exc))
                    continue
                valid=bool(state["valid"])
                if state["applied"] and not valid:
                    snapshot=None
                    await store.quality(symbol,"DEPTH","INVALID",value.get("E"),"empty local book; resnapshot")
                elif valid:
                    await store.mutate("market_observations","update_one",{"venue":VENUE,"symbol":symbol,"kind":"BOOK"},{"$set":{"venue":VENUE,"symbol":symbol,"kind":"BOOK","source_time_ms":value["E"],"received_at_ms":now_ms,"last_update_id":state["last_update_id"],"valid":True,"snapshot_limit":1000,"bid_levels":state["bid_levels"],"ask_levels":state["ask_levels"],"best_bid":state["best_bid"],"best_ask":state["best_ask"],"epoch":epoch,"fence":store.fence}},upsert=True)
            elif kind=="kline":
                try: normalized=await store.normalize("kline",value)
                except ValueError:
                    await store.quality(symbol,"CANDLE","INVALID",value.get("E"),"malformed live candle"); continue
                if normalized["symbol"]!=symbol: continue
                counts["kline"]+=1; normalized.pop("ok"); doc={**normalized,"venue":VENUE,"source":"BINANCE_WS","received_at_ms":now_ms}
                await save_candle(store,doc)
            elif kind=="markPriceUpdate":
                try: normalized=await store.normalize("mark",value)
                except ValueError:
                    await store.quality(symbol,"MARK","INVALID",value.get("E"),"malformed mark event"); continue
                if normalized["symbol"]!=symbol: continue
                counts["mark"]+=1; normalized.pop("ok")
                await store.mutate("market_observations","update_one",{"venue":VENUE,"symbol":symbol,"kind":"MARK"},{"$set":{**normalized,"venue":VENUE,"kind":"MARK","received_at_ms":now_ms,"fence":store.fence}},upsert=True)
            elif kind=="aggTrade":
                try: normalized=await store.normalize("agg_trade",value)
                except ValueError:
                    await store.quality(symbol,"AGG_TRADE","INVALID",value.get("T"),"malformed aggregate trade"); continue
                if normalized["symbol"]!=symbol: continue
                counts["trade"]+=1; normalized.pop("ok")
                await store.mutate("market_observations","update_one",{"venue":VENUE,"symbol":symbol,"kind":"AGG_TRADE"},{"$set":{**normalized,"venue":VENUE,"kind":"AGG_TRADE","received_at_ms":now_ms,"fence":store.fence}},upsert=True)
            if valid and counts["mark"] and counts["kline"] and not signaled_live:
                await store.quality(symbol,"STREAM","LIVE",detail="acknowledged routed streams; synchronized depth")
                signaled_live=True
        await receiver; await process.wait(); errors=(await process.stderr.read()).decode(errors="replace")
        if process.returncode: raise RuntimeError("stream helper failed: "+errors[:120])
        state="LIVE" if counts["mark"] and counts["kline"] and counts["depth"] and valid and acked=={"market","public"} else "DEGRADED"
        await store.quality(symbol,"STREAM",state,detail=json.dumps(counts))
        if state != "LIVE": raise RuntimeError("public stream did not reach synchronized LIVE state")
        return counts
    finally:
        if process.returncode is None: process.terminate(); await process.wait()
        if not receiver.done(): receiver.cancel()
        await asyncio.gather(receiver,return_exceptions=True)
        await store.quality(symbol,"STREAM","DISCONNECTED",detail="bounded collector stream stopped")


async def run(database:str,symbol:str,seconds:int,start_ms:int,cycles:int=1)->dict[str,Any]:
    mongo=AsyncMongoClient(os.getenv("QUANTORA_MONGO_URL","mongodb://127.0.0.1:27117/?directConnection=true&replicaSet=quantora-rs"),serverSelectionTimeoutMS=3000); store=Store(mongo[database],str(uuid4()))
    store.continuous=cycles==0
    from quantora_api.market import migrate_market
    if not await store.db.migrations.find_one({"_id": "v1"}):
        await mongo.close()
        raise RuntimeError("Phase 3 v1 migration must be applied before Phase 4")
    await migrate_market(store.db); await store.acquire()
    async def heartbeat()->None:
        while True:
            await asyncio.sleep(10)
            await store.renew()
    keeper=asyncio.create_task(heartbeat())
    try:
        store.processor=await MarketProcessor.start()
        async with httpx.AsyncClient(timeout=10, trust_env=False) as http:
            universe=await discover(store,http)
            if symbol not in universe: raise RuntimeError("symbol is not eligible")
            last_discovery=time.monotonic(); completed=0; bars=0; polled={}; counts={}
            while cycles==0 or completed<cycles:
                if keeper.done(): await keeper
                if time.monotonic()-last_discovery>=900:
                    universe=await discover(store,http)
                    if symbol not in universe: raise RuntimeError("selected symbol no longer eligible")
                    last_discovery=time.monotonic()
                for interval in ("1m","5m","15m"):
                    bars+=await backfill(store,http,symbol,interval,start_ms,int(time.time()*1000))
                polled=await poll_oi_funding(store,http,symbol)
                for attempt in range(3):
                    if keeper.done(): await keeper
                    worker=asyncio.create_task(stream(store,http,symbol,seconds))
                    done,_=await asyncio.wait({keeper,worker},return_when=asyncio.FIRST_COMPLETED)
                    if keeper in done:
                        worker.cancel()
                        await asyncio.gather(worker,return_exceptions=True)
                        await keeper
                    try:
                        counts=await worker
                        break
                    except RuntimeError:
                        if attempt==2: raise
                        await store.quality(symbol,"STREAM","INVALID",detail="reconnecting with fresh book snapshot")
                        await asyncio.sleep(min(2**attempt+random.random(),5))
                completed+=1
                await store.renew()
            return {"status":"PASS","database":database,"symbol":symbol,"eligible":len(universe),"backfill_rows":bars,"poll_counts":polled,"stream_counts":counts,"fence":store.fence,"cycles":completed}
    finally:
        keeper.cancel()
        await asyncio.gather(keeper,return_exceptions=True)
        if store.processor: await store.processor.close()
        await store.release(); await mongo.close()


def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--database",required=True); parser.add_argument("--symbol",default="BTCUSDT"); parser.add_argument("--seconds",type=int); parser.add_argument("--continuous",action="store_true"); parser.add_argument("--start-ms",type=int,default=int(time.time()*1000)-3_600_000); args=parser.parse_args()
    if not args.database.startswith("quantora_"): raise SystemExit("refusing non-Quantora database")
    seconds=args.seconds if args.seconds is not None else (300 if args.continuous else 15)
    if seconds<1 or seconds>300 or args.start_ms<0 or args.start_ms>=int(time.time()*1000): raise SystemExit("invalid bounded collector range")
    print(json.dumps(asyncio.run(run(args.database,args.symbol,seconds,args.start_ms,0 if args.continuous else 1)),sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
