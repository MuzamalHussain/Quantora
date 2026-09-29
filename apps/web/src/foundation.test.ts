import { describe, expect, it } from 'vitest';
import cases from '../../../contracts/fixtures.json';
import { parseEnvelope } from './contracts';
import { aggregate, candles } from './fixtures';

describe('canonical transport contracts', () => {
  for (const fixture of cases) it(fixture.name, () => {
    if (fixture.valid) expect(() => parseEnvelope(fixture.value)).not.toThrow();
    else expect(() => parseEnvelope(fixture.value)).toThrow();
  });
  it('rejects nonfinite JSON-domain values', () => {
    const value = structuredClone(cases[3].value);
    (value.payload as { probabilities: { up: number } }).probabilities.up = NaN;
    expect(() => parseEnvelope(value)).toThrow();
  });
});
describe('timeframe aggregation', () => {
  it('preserves OHLC and volume rather than relabeling timestamps', () => {
    const source = candles(); const result = aggregate(source, 5);
    expect(result).toHaveLength(36);
    expect(result[0].open).toBe(source[0].open);
    expect(result[0].close).toBe(source[4].close);
    expect(result[0].high).toBe(Math.max(...source.slice(0, 5).map(b => b.high)));
    expect(result[0].low).toBe(Math.min(...source.slice(0, 5).map(b => b.low)));
    expect(result.reduce((a, b) => a + b.volume, 0)).toBe(source.reduce((a, b) => a + b.volume, 0));
    expect(aggregate(source, 15)).toHaveLength(12);
    expect(source).toEqual(candles());
    expect(() => aggregate(source, 2)).toThrow();
  });
});
