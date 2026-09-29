import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  reporter: [['list']],
  outputDir: '.cache/browser-results',
  use: { browserName: 'chromium', channel: process.env.QUANTORA_BROWSER_CHANNEL || 'msedge',
    headless: true, baseURL: 'http://127.0.0.1:4173', screenshot: 'only-on-failure' },
  webServer: process.env.QUANTORA_EXTERNAL_PREVIEW === '1' ? undefined : { command: 'node node_modules/vite/bin/vite.js preview apps/web --host 127.0.0.1 --port 4173 --strictPort', url: 'http://127.0.0.1:4173',
    reuseExistingServer: false, timeout: 30000 },
});
