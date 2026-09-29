import { expect, test } from '@playwright/test';
import { mkdirSync } from 'node:fs';

test('chart, aggregation, resizing, labels, keyboard and real service response', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  const responsePromise = page.waitForResponse('**/api/v1/foundation/status');
  await page.goto('/');
  const statusResponse = await responsePromise;
  const status = await statusResponse.json();
  expect(status.event_type).toBe('HEALTH');
  expect(status.source.kind).toBe('FOUNDATION');
  expect(status.payload.trading_enabled).toBe(false);
  await expect(page.getByRole('button', { name: 'Start session' })).toBeDisabled();
  await expect(page.getByText('Fixture data — deterministic demo', { exact: false })).toBeVisible();
  await expect(page.locator('.services > div').filter({ has: page.getByText('Rust core', { exact: true }) }).locator('dd')).toHaveText(status.payload.dependencies.core);
  await expect(page.locator('canvas').first()).toBeVisible();
  // Canvas pixels must contain both candle colors, not only an empty canvas shell.
  const candlePixels = await page.locator('.chart').evaluate(element => {
    const counts = [0, 0];
    for (const canvas of element.querySelectorAll('canvas')) {
      const data = canvas.getContext('2d')!.getImageData(0, 0, canvas.width, canvas.height).data;
      for (let i = 0; i < data.length; i += 4) {
        if (data[i] === 101 && data[i + 1] === 216 && data[i + 2] === 176) counts[0]++;
        if (data[i] === 238 && data[i + 1] === 141 && data[i + 2] === 138) counts[1]++;
      }
    }
    return counts;
  });
  expect(candlePixels[0]).toBeGreaterThan(100);
  expect(candlePixels[1]).toBeGreaterThan(100);
  await page.getByRole('button', { name: '5m', exact: true }).click();
  await expect(page.locator('.chart-number')).toHaveText('36 bars');
  await expect(page.getByRole('img', { name: /Synthetic 5-minute/ })).toBeVisible();
  await page.getByRole('button', { name: '15m', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.chart-number')).toHaveText('12 bars');
  await page.getByRole('tab', { name: 'Orders' }).click();
  await expect(page.getByRole('tabpanel')).toContainText('No orders in foundation');
  await page.getByRole('button', { name: 'Settings' }).click();
  await expect(page.getByRole('heading', { name: 'Integrations', exact: true })).toBeVisible();
  mkdirSync('docs/phase-02/evidence', { recursive: true });
  for (const width of [1440, 768, 360]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect.poll(async () => page.locator('.chart').evaluate(e => e.clientWidth)).toBeGreaterThan(250);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await expect(page.locator('.badge')).toHaveText('FOUNDATION');
    await page.screenshot({ path: `docs/phase-02/evidence/workspace-${width}.png`, fullPage: true });
  }
  expect(errors).toEqual([]);
});

test('unreachable responses do not remain current (browser fault injection)', async ({ page }) => {
  await page.route('**/api/v1/foundation/status', route => route.abort());
  await page.goto('/');
  await expect(page.locator('.services')).toContainText('Unavailable');
  await expect(page.locator('.mode-card')).toContainText('UNCONFIRMED');
  await expect(page.locator('.checked')).toContainText('no current dependency evidence');
});
