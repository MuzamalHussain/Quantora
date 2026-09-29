# Chart engine evaluation

Official source review occurred on 2026-09-15; source links and limits are in sources.md. Only the selected engine was installed and prototyped. No comparative benchmark was executed.

| Criterion | Lightweight Charts 5.2.1 | Apache ECharts alternative |
|---|---|---|
| Candles and volume | Candlestick and histogram series; both implemented | General chart library with financial chart composition; not prototyped here |
| Custom feed | Application supplies deterministic arrays; future streaming adapter is separate | Application supplies chart data; integration not evaluated locally |
| React / TypeScript | Typed library integrated through a React lifecycle/ref; chart removed on cleanup | General JavaScript/TypeScript integration would need equivalent lifecycle wrapper |
| Overlays | Price line implemented; series/plugin APIs available | General composition/graphics API; financial interaction would need design |
| Indicators/drawings | Application calculations and primitives/plugins; no claim of bundled terminal tools | Custom configuration/graphics; no terminal-parity assumption |
| License | Apache-2.0 plus official NOTICE and TradingView attribution link | Official repository Apache-2.0; unselected, no assets shipped |
| Performance | Browser rendering and resizing demonstrated with 180 synthetic 1m bars; no large-feed/latency benchmark | Not measured |

Selected Lightweight Charts is accessible without proprietary TradingView access and has an evaluated financial-series integration. The installed release's full LICENSE and NOTICE are included in apps/web/public; the visible footer includes TradingView attribution. Apache-2.0 permits commercial use subject to its conditions; no proprietary Advanced Charts rights or universal legal compliance is asserted.

## Implemented demonstration

The fixture generator uses a fixed epoch and deterministic prices/volume. 5m and 15m grouping produces valid open/maximum high/minimum low/final close/summed volume (36 and 12 bars from 180 minutes). The chart uses candles, a volume histogram and a horizontal fixture-reference price at 100. ResizeObserver-backed autoSize follows the available region. FOUNDATION/FIXTURE labels and a fixed synthetic timestamp prevent market-data confusion.

Browser checks inspect colored candle pixels, nonempty canvas, keyboard timeframe switching, true aggregation counts, responsive widths, disabled controls, service response and honest unavailable state. Screenshots are evidence/workspace-1440.png, workspace-768.png and workspace-360.png. Actual run status belongs to verification-matrix.md; screenshot existence alone is not a PASS.

QNT-FR-0015's proposed SMA, EMA, RSI, MACD, ATR, editable horizontal/trend lines and rectangles remain Phase 11 work. The sample price line is not a complete drawing editor. Saved workspaces, live feeds, forecasts, trading overlays and full TradingView feature parity are not implemented. Canvas is supplemented by labels and controls, but does not establish full screen-reader chart accessibility.
