import { useEffect, useRef } from 'react';
import { CandlestickSeries, ColorType, HistogramSeries, createChart, type UTCTimestamp } from 'lightweight-charts';
import { aggregate, candles, type Candle } from './fixtures';

export function Chart({ minutes, liveBars }: { minutes: number; liveBars?: Candle[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const container = ref.current;
    if (!container) return;
    const chart = createChart(container, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: '#10171a' }, textColor: '#b5c4c8', attributionLogo: true },
      grid: { vertLines: { color: '#1a252a' }, horzLines: { color: '#1a252a' } },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2a393e' },
      rightPriceScale: { borderColor: '#2a393e' },
    });
    const price = chart.addSeries(CandlestickSeries, { upColor: '#65d8b0', downColor: '#ee8d8a', borderVisible: false, wickUpColor: '#65d8b0', wickDownColor: '#ee8d8a' });
    const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: 'volume' });
    price.priceScale().applyOptions({ scaleMargins: { top: 0.09, bottom: 0.25 } });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    const bars = liveBars ?? aggregate(candles(), minutes);
    price.setData(bars.map(b => ({ ...b, time: b.time as UTCTimestamp })));
    volume.setData(bars.map(b => ({ time: b.time as UTCTimestamp, value: b.volume, color: b.close >= b.open ? '#265747' : '#583b3c' })));
    if (!liveBars) price.createPriceLine({ price: 100, color: '#dfc179', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'Fixture reference' });
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [minutes, liveBars]);
  return <div ref={ref} className="chart" role="img" aria-label={`${liveBars ? 'Binance USD-M public' : 'Synthetic'} ${minutes}-minute candlestick chart with volume`} />;
}
