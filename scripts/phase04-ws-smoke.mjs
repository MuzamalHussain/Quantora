import { mkdir, writeFile } from 'node:fs/promises';

const url = 'wss://fstream.binance.com/market/ws';
const stream = 'btcusdt@markPrice@1s';
const started = Date.now();
const diagnostic = {
  schema_version: 1, observed_at_utc: new Date().toISOString(), url, stream,
  route: 'market', symbol_casing: 'lowercase', credentials_used: false,
  proxy_environment: { https_proxy_present: Boolean(process.env.HTTPS_PROXY || process.env.https_proxy), no_proxy_present: Boolean(process.env.NO_PROXY || process.env.no_proxy) },
  events: [], result: 'IN_PROGRESS'
};
const note = (type, detail = {}) => diagnostic.events.push({ elapsed_ms: Date.now() - started, type, ...detail });

await new Promise((resolve, reject) => {
  const ws = new WebSocket(url);
  let acknowledged = false;
  const timer = setTimeout(() => { note('timeout'); ws.close(1000, 'bounded smoke complete'); reject(new Error('public WebSocket data timeout')); }, 15000);
  ws.addEventListener('open', () => {
    note('open');
    ws.send(JSON.stringify({ method: 'SUBSCRIBE', params: [stream], id: 1 }));
    note('subscription_sent', { id: 1 });
  });
  ws.addEventListener('message', event => {
    try {
      const value = JSON.parse(String(event.data));
      if (value.id === 1 && value.result === null) { acknowledged = true; note('subscription_ack', { id: 1 }); return; }
      if (value.e === 'markPriceUpdate' && value.s === 'BTCUSDT') {
        note('data', { event_type: value.e, symbol: value.s, event_time_ms: value.E, mark_price_present: Boolean(value.p), index_price_present: Boolean(value.i) });
        diagnostic.result = acknowledged ? 'PASS' : 'FAIL_NO_ACK';
        clearTimeout(timer); ws.close(1000, 'bounded smoke complete'); resolve();
      } else note('unexpected_data', { keys: Object.keys(value).sort() });
    } catch (error) { note('parse_error', { name: error.name }); }
  });
  ws.addEventListener('error', () => note('error'));
  ws.addEventListener('close', event => note('close', { code: event.code, clean: event.wasClean, reason: event.reason || null }));
});
await new Promise(resolve => setTimeout(resolve, 50));
await mkdir('docs/phase-04/evidence', { recursive: true });
await writeFile('docs/phase-04/evidence/live-websocket.json', JSON.stringify(diagnostic, null, 2));
console.log(JSON.stringify({status: diagnostic.result, evidence:'docs/phase-04/evidence/live-websocket.json'}));
if (diagnostic.result !== 'PASS') process.exitCode = 1;
