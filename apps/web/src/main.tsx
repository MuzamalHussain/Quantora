import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { MarketWorkspace } from './MarketWorkspace';
import { Account } from './Account';
import { parseEnvelope } from './contracts';
import './styles.css';

type ServiceState = { api: string; core: string; mongodb: string; redis: string; mode: string; checked: string };
const initial: ServiceState = { api: 'Checking', core: 'Unknown', mongodb: 'Unknown', redis: 'Unknown', mode: 'UNCONFIRMED', checked: 'Awaiting response' };

function App() {
  const [minutes, setMinutes] = useState(1);
  const [marketMode, setMarketMode] = useState<'fixture'|'live'>('fixture');
  const [tab, setTab] = useState('Positions');
  const [settings, setSettings] = useState(false);
  const [status, setStatus] = useState<ServiceState>(initial);
  useEffect(() => {
    let disposed = false;
    let controller: AbortController | undefined;
    async function update() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller?.abort(), 1800);
      try {
        const response = await fetch('/api/v1/foundation/status', { signal: controller.signal, cache: 'no-store' });
        const value = parseEnvelope(await response.json());
        if (value.event_type !== 'HEALTH' || value.payload.service !== 'control-api' || value.source.kind !== 'FOUNDATION') throw new Error('Unexpected service');
        const age = Date.now() - value.occurred_at_ms;
        if (age > 10000 || age < -5000) throw new Error('Stale service status');
        if (!disposed) setStatus({ api: value.payload.status === 'READY' ? 'Ready' : 'Not ready', ...value.payload.dependencies,
          mode: value.mode, checked: `Checked ${new Date().toLocaleTimeString()}` });
      } catch {
        if (!disposed) setStatus({ ...initial, api: 'Unavailable', checked: 'Status unavailable — no current dependency evidence' });
      } finally { clearTimeout(timeout); }
    }
    void update();
    const timer = setInterval(() => { void update(); }, 5000);
    return () => { disposed = true; clearInterval(timer); controller?.abort(); };
  }, []);

  return <div className="app">
    <header className="top"><a className="brand" href="#workspace" aria-label="Quantora workspace"><span className="mark">Q</span> QUANTORA<span className="version">/ 02</span></a>
      <div className="context"><span className="badge">FOUNDATION</span><span className="muted">Local development workspace</span></div>
      <button className="settings-button" onClick={() => setSettings(v => !v)} aria-expanded={settings}>Settings <span aria-hidden="true">↗</span></button>
      <a className="account-link" href="#account">Account</a>
    </header>
    <div className="notice"><span className="notice-dot"/> Public market-data foundation. <span>LIVE MARKET DATA never enables trading · execution disabled</span></div>
    <Account/>
    <main id="workspace" className="workspace">
      <aside className="watch panel"><div className="panel-heading"><h2>Market workspace</h2><span className="small">01</span></div>
        <label htmlFor="search">Symbol search</label><input id="search" placeholder="Available in a later phase" disabled />
        <div className="section-label">{marketMode==='live' ? 'PUBLIC BINANCE UNIVERSE' : 'FIXTURE COLLECTION'}</div>{marketMode==='fixture' && <div className="fixture-item"><span className="fixture-icon">F</span><div><strong>SYNTH / USDT</strong><span>Synthetic instrument</span></div><span className="selected-dot"/></div>}
        <div className="empty-universe"><span className="empty-symbol">◎</span><h3>{marketMode==='live' ? 'Shared market feed' : 'No connected universe'}</h3><p>{marketMode==='live' ? 'Select an eligible contract beside the chart. Collection runs once for the shared service.' : 'Watchlists and the market scanner arrive after ingestion is implemented.'}</p></div>
        <div className="side-note"><span className="section-label">SCOPE</span><p>Binance USDT-margined perpetuals are the planned initial venue scope. This fixture is not a listed contract.</p></div>
      </aside>
      <section className="center panel" aria-labelledby="chart-title"><div className="instrument-head"><div><div className="eyebrow">CHART FEASIBILITY</div><h1 id="chart-title">{marketMode==='live' ? 'Binance public market' : 'Synthetic market'} <span className="fixture-badge">{marketMode==='live' ? 'PUBLIC' : 'FIXTURE'}</span></h1><p>{marketMode==='live' ? 'Stored Binance USDⓈ-M perpetual candles · public read only' : 'Deterministic candles & volume · 01 Jan 2026 UTC'}</p></div><span className="chart-number">{180 / minutes} bars</span></div>
        <div className="chart-tools"><div role="group" aria-label="Chart timeframe">{[1, 5, 15].map(n => <button key={n} aria-pressed={minutes === n} className={minutes === n ? 'active' : ''} onClick={() => setMinutes(n)}>{n}m</button>)}</div><span>OHLC aggregation <span aria-hidden="true">·</span> Volume</span></div>
        <MarketWorkspace minutes={minutes} mode={marketMode} setMode={setMarketMode}/><div className="chart-foot"><span className="legend-line"/>Public data is informational and never execution-ready by itself</div>
        <div className="history"><div className="tabs" role="tablist" aria-label="Account records">{['Positions', 'Orders', 'History'].map(t => <button role="tab" aria-selected={t === tab} id={`tab-${t}`} aria-controls="record-panel" key={t} onClick={() => setTab(t)}>{t}</button>)}</div>
          <div className="empty-record" role="tabpanel" id="record-panel" aria-labelledby={`tab-${tab}`}><div className="empty-glyph">―</div><h3>No {tab.toLowerCase()} in foundation</h3><p>Account management and execution are not implemented. No balance or performance is simulated here.</p></div></div>
      </section>
      <aside className="control panel"><div className="panel-heading"><h2>{settings ? 'Settings & boundaries' : 'Foundation controls'}</h2><span className="small">02</span></div>
        <div className="mode-card"><span className="section-label">TRANSPORT MODE</span><strong>{status.mode}</strong><span>Execution always disabled</span></div>
        {settings && <div className="settings-info"><h3>Integrations</h3><p>Dashboard-managed provider credentials are planned. Storage and connection tests are unavailable in this foundation.</p></div>}
        <div className="disabled-controls"><button disabled>Start session <span>↗</span></button><div><button disabled>Pause</button><button disabled>Stop</button></div><p>No trading routes or order authority exist.</p></div>
        <div className="section-label service-label">SERVICE STATUS <span>ACTUAL CHECKS</span></div>
        <dl className="services" aria-live="polite">{[['Control API', status.api], ['Rust core', status.core], ['MongoDB', status.mongodb], ['Redis', status.redis]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd className={['UP', 'Ready'].includes(value) ? 'up' : 'down'}><span/> {value}</dd></div>)}</dl>
        <p className="checked">{status.checked}</p>
        <div className="boundary-note"><h3>Deliberately bounded</h3><p>Risk rules will override models. Closing exposure and opening the opposite side remain independent decisions.</p><span>FLAT and NO TRADE are valid outcomes.</span></div>
      </aside>
    </main>
    <footer><span>QUANTORA <span className="muted">/ Foundation, not trading readiness</span></span><a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView Lightweight Charts™ · Copyright (с) 2025 TradingView, Inc.</a></footer>
  </div>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
