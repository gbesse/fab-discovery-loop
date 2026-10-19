import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
const port = 18765,
  base = `http://127.0.0.1:${port}`;
const server = spawn(
  process.env.PYTHON || 'python3',
  ['-m', 'fab_discovery', 'serve', String(port)],
  { stdio: ['ignore', 'pipe', 'inherit'] },
);
let browser;
try {
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {}
    if (server.exitCode !== null) throw Error('server exited');
    if (i === 99) throw Error('server timeout');
    await new Promise((r) => setTimeout(r, 100));
  }
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1300, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  for (const lang of ['fr', 'en', 'es']) {
    await page.goto(`${base}/?lang=${lang}`);
    await page.waitForFunction(
      () => document.getElementById('recommendation').textContent === 'p3-d2',
    );
    assert.equal(await page.locator('html').getAttribute('lang'), lang);
    await page.locator('#simulate').click();
    await page.waitForFunction(() => document.getElementById('count').textContent === '1');
    assert.equal(await page.locator('#budget').textContent(), '21.0');
    assert.equal(await page.locator('.observation').count(), 1);
    assert.notEqual(await page.locator('#entropy').textContent(), '1.585');
    await page.locator('#risk').fill('0');
    await page.locator('#risk').dispatchEvent('change');
    await page.waitForFunction(() => document.getElementById('simulate').disabled);
    assert.equal(await page.locator('tr.recommended').count(), 0);
    await page.locator('#reset').click();
    await page.waitForFunction(() => document.getElementById('count').textContent === '0');
    await page.locator('summary').click();
    await page.locator('#outcome').selectOption('damaged');
    await page.locator('#record').click();
    await page.waitForFunction(() => document.getElementById('count').textContent === '1');
    const event = page.waitForEvent('download');
    await page.locator('#download').click();
    assert.equal((await event).suggestedFilename(), 'fab-discovery-evidence.json');
  }
  await page.goto(`${base}/?lang=fr`);
  await page.waitForFunction(
    () => document.getElementById('recommendation').textContent === 'p3-d2',
  );
  await mkdir('.local', { recursive: true });
  await page.screenshot({ path: '.local/preview-fr.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  assert.deepEqual(errors, []);
  const response = await fetch(base + '/api/analyze', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ case: [] }),
  });
  assert.equal(response.status, 400);
  console.log(
    'FR/EN/ES: simulated and entered observations, risk exclusion, reset, export and mobile verified.',
  );
} finally {
  if (browser) await browser.close();
  server.kill('SIGTERM');
}
