import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import path from 'node:path';

test.skip(process.env.QUANTORA_PHASE4_BROWSER !== '1', 'Phase 4 runner owns isolated market evidence');
test('authenticated stored public chart, timeframe isolation and explicit disconnect', async ({page}) => {
  if (process.env.QUANTORA_PHASE4_LIVE_DB === '1') test.setTimeout(120_000);
  const email=`market-${Date.now()}@example.test`;
  await page.goto('/#account');
  await page.getByRole('button',{name:'Create account',exact:true}).click();
  await page.getByLabel('Email',{exact:true}).fill(email);
  await page.getByLabel('Password',{exact:true}).fill('Synthetic-browser-password-73!');
  await page.getByRole('button',{name:'Register',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'Registration processed'})).toContainText('Registration processed');
  await page.getByRole('button',{name:'Use existing account'}).click();
  await page.getByLabel('Email',{exact:true}).fill(email);
  await page.getByLabel('Password',{exact:true}).fill('Synthetic-browser-password-73!');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByTestId('signed-in')).toContainText(email);
  if (process.env.QUANTORA_PHASE4_LIVE_DB !== '1') {
    execFileSync(path.resolve('.venv/Scripts/python.exe'), ['scripts/phase03_test_control.py','seed-market',email], {stdio:'pipe'});
  }
  await page.getByRole('link',{name:'Back to fixture workspace'}).click();
  await page.getByRole('button',{name:'Live public feed'}).click();
  await expect(page.getByRole('heading',{name:'Binance public market'})).toBeVisible();
  await expect(page.getByRole('combobox',{name:'Eligible Binance instrument'})).toHaveValue('BTCUSDT');
  await expect(page.getByRole('status').filter({hasText:'stored Binance USD-M'})).toContainText('BTCUSDT · 1m');
  await expect(page.locator('canvas').first()).toBeVisible();
  await page.getByRole('button',{name:'5m',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'stored Binance USD-M'})).toContainText('BTCUSDT · 5m');
  if (process.env.QUANTORA_PHASE4_LIVE_DB === '1') {
    await page.getByRole('button',{name:'15m',exact:true}).click();
    await expect(page.getByRole('status').filter({hasText:'stored Binance USD-M'})).toContainText('BTCUSDT · 15m');
    await page.getByRole('button',{name:'1m',exact:true}).click();
    const status=page.getByRole('status').filter({hasText:'stored Binance USD-M'});
    const before=Number((await status.innerText()).match(/received (\d+)/)?.[1] ?? 0);
    expect(before).toBeGreaterThan(0);
    const output=execFileSync(path.resolve('.venv/Scripts/python.exe'), [
      'scripts/phase04_collector.py','--database',process.env.QUANTORA_DATABASE!,
      '--symbol','BTCUSDT','--seconds','15','--start-ms',String(Date.now()-3_600_000),
    ], {stdio:'pipe',timeout:90_000,encoding:'utf8'});
    const run=JSON.parse(output) as {status:string;fence:number;stream_counts:{kline:number;depth:number}};
    expect(run.status).toBe('PASS');
    expect(run.stream_counts.kline).toBeGreaterThan(0);
    expect(run.stream_counts.depth).toBeGreaterThan(0);
    await expect.poll(async () => {
      const text=await status.innerText();
      const received=Number(text.match(/received (\d+)/)?.[1] ?? 0);
      return text.includes('BINANCE_WS') && received>before;
    },{timeout:15_000}).toBe(true);
    const after=Number((await status.innerText()).match(/received (\d+)/)?.[1] ?? 0);
    if(process.env.QUANTORA_PHASE4_BROWSER_EVIDENCE){
      writeFileSync(process.env.QUANTORA_PHASE4_BROWSER_EVIDENCE,JSON.stringify({schema_version:1,source:'BINANCE_WS',symbol:'BTCUSDT',interval:'1m',before_received_at_ms:before,after_received_at_ms:after,collector_fence:run.fence,stream_counts:run.stream_counts,chart_visible:await page.locator('canvas').first().isVisible()},null,2)+'\n');
    }
    await expect(page.locator('canvas').first()).toBeVisible();
  }
  await expect(page.getByRole('button',{name:'Start session'})).toBeDisabled();
  await page.route('**/api/v1/market/**', route=>route.abort());
  await page.getByRole('button',{name:'Fixture'}).click();
  await page.getByRole('button',{name:'Live public feed'}).click();
  await expect(page.getByRole('status').filter({hasText:'disconnected'})).toContainText('no synthetic fallback');
  for (const width of [1440,768,360]) { await page.setViewportSize({width,height:900}); expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true); await page.screenshot({path:`docs/phase-04/evidence/market-${width}.png`,fullPage:true}); }
});
