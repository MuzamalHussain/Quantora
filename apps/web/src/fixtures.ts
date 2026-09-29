export type Candle = { time: number; open: number; high: number; low: number; close: number; volume: number };

// Entirely synthetic. Fixed UTC epoch and arithmetic; no random or network input.
export function candles(): Candle[] {
  let last = 100;
  return Array.from({ length: 180 }, (_, i) => {
    const open = last;
    const close = Math.round((open + Math.sin(i * 0.29) * 0.65 + Math.cos(i * 0.09) * 0.18 + 0.04) * 100) / 100;
    last = close;
    return { time: 1767225600 + i * 60, open, close,
      high: Math.max(open, close) + 0.35 + (i % 5) * 0.06,
      low: Math.min(open, close) - 0.31 - (i % 3) * 0.08,
      volume: 1000 + ((i * 7919) % 3500) };
  });
}

export function aggregate(input: Candle[], minutes: number): Candle[] {
  if (![1, 5, 15].includes(minutes)) throw new Error('Unsupported fixture timeframe');
  const groups = new Map<number, Candle>();
  for (const bar of input) {
    const time = Math.floor(bar.time / (minutes * 60)) * minutes * 60;
    const current = groups.get(time);
    if (current) {
      current.high = Math.max(current.high, bar.high);
      current.low = Math.min(current.low, bar.low);
      current.close = bar.close;
      current.volume += bar.volume;
    } else groups.set(time, { ...bar, time });
  }
  return [...groups.values()];
}
