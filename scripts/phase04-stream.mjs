// Bounded public transport helper. It emits provider JSON only; Rust/Python collector owns state.
const symbol=(process.env.QUANTORA_MARKET_SYMBOL || 'BTCUSDT').toLowerCase();
const seconds=Math.min(Math.max(Number(process.env.QUANTORA_COLLECTOR_SECONDS || 15),1),300);
const configs=[
  ['market',`wss://fstream.binance.com/market/ws`,[`${symbol}@kline_1m`,`${symbol}@kline_5m`,`${symbol}@kline_15m`,`${symbol}@markPrice@1s`,`${symbol}@aggTrade`]],
  ['public',`wss://fstream.binance.com/public/ws`,[`${symbol}@depth@100ms`]],
];
const sockets=[];
let failed=false;
let stopping=false;
for(const [route,url,streams] of configs){
  const ws=new WebSocket(url); sockets.push(ws);
  ws.addEventListener('open',()=>ws.send(JSON.stringify({method:'SUBSCRIBE',params:streams,id:route==='market'?1:2})));
  ws.addEventListener('message',event=>{
    try { const value=JSON.parse(String(event.data)); process.stdout.write(JSON.stringify({route,received_at_ms:Date.now(),value})+'\n'); }
    catch { failed=true; process.stderr.write(JSON.stringify({event:'parse_error',route})+'\n'); }
  });
  ws.addEventListener('error',()=>{failed=true;process.stderr.write(JSON.stringify({event:'websocket_error',route})+'\n');});
  ws.addEventListener('close',event=>{if(!stopping) failed=true;process.stderr.write(JSON.stringify({event:'close',route,code:event.code,clean:event.wasClean})+'\n');});
}
setTimeout(()=>{stopping=true;for(const ws of sockets) ws.close(1000,'bounded collector stop'); setTimeout(()=>process.exit(failed?1:0),100);},seconds*1000);
