import { useEffect, useState } from 'react';
import { Chart } from './Chart';
import type { Candle } from './fixtures';

type Instrument = { symbol: string; eligible: boolean; status: string };
type ApiCandle = { open_time_ms: number; open: string; high: string; low: string; close: string; volume: string; source?: string; received_at_ms?: number };

export function MarketWorkspace({ minutes, mode, setMode }: { minutes: number; mode: 'fixture'|'live'; setMode: (mode:'fixture'|'live')=>void }) {
  const [symbols, setSymbols] = useState<Instrument[]>([]);
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [bars, setBars] = useState<Candle[]>([]);
  const [state, setState] = useState('Fixture data — deterministic demo');
  useEffect(() => {
    if (mode === 'fixture') { setBars([]); setState('Fixture data — deterministic demo'); return; }
    const controller = new AbortController();
    async function load() {
      try {
        setState('Loading stored Binance public data…');
        const universe:Instrument[]=[];
        for(let offset=0;offset<=5000;offset+=500){
          const ir = await fetch(`/api/v1/market/instruments?limit=500&offset=${offset}`, { credentials:'same-origin', signal:controller.signal });
          if (!ir.ok) throw new Error();
          const iv = await ir.json() as {items:Instrument[];next_offset:number|null};
          universe.push(...iv.items);
          if(iv.next_offset===null) break;
        }
        setSymbols(universe);
        const end=Date.now(), start=end-200*minutes*60_000;
        const cr=await fetch(`/api/v1/market/candles?symbol=${encodeURIComponent(symbol)}&interval=${minutes}m&start_ms=${start}&end_ms=${end}&limit=500`, {credentials:'same-origin',signal:controller.signal});
        if (!cr.ok) throw new Error();
        const cv=await cr.json() as {items:ApiCandle[]};
        const sr=await fetch(`/api/v1/market/snapshot?symbol=${encodeURIComponent(symbol)}`,{credentials:'same-origin',signal:controller.signal});
        if(!sr.ok) throw new Error();
        const sv=await sr.json() as {public_feed_state:string;feed_age_ms:number|null};
        setBars(cv.items.map(b=>({time:Math.floor(b.open_time_ms/1000),open:Number(b.open),high:Number(b.high),low:Number(b.low),close:Number(b.close),volume:Number(b.volume)})));
        const latest=cv.items.at(-1);
        setState(latest ? `Public feed ${sv.public_feed_state.toLowerCase()} · ${symbol} · ${minutes}m · stored Binance USD-M · ${latest.source ?? 'unknown source'} · received ${latest.received_at_ms ?? 0}` : `Public feed ${sv.public_feed_state.toLowerCase()} · no stored live candles — no synthetic fallback`);
      } catch { setBars([]); setState('Public feed disconnected or sign-in required — no synthetic fallback'); }
    }
    void load();
    const refresh = window.setInterval(() => { if (!controller.signal.aborted) void load(); }, 3000);
    return () => { window.clearInterval(refresh); controller.abort(); };
  }, [mode, symbol, minutes]);
  return <><div className="market-source"><button aria-pressed={mode==='fixture'} onClick={()=>setMode('fixture')}>Fixture</button><button aria-pressed={mode==='live'} onClick={()=>setMode('live')}>Live public feed</button>{mode==='live' && <select aria-label="Eligible Binance instrument" value={symbol} onChange={e=>setSymbol(e.target.value)}>{symbols.filter(x=>x.eligible).map(x=><option key={x.symbol}>{x.symbol}</option>)}</select>}</div><p className="feed-state" role="status">{state}</p><Chart minutes={minutes} liveBars={mode==='live' ? bars : undefined}/></>;
}
