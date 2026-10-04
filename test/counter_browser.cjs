'use strict';
// Run with PLAYWRIGHT_MODULE and optional CHROMIUM_EXECUTABLE set locally.
// Requests are intercepted: .test is a fixture, never a public endpoint.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {spawn} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const evidence = path.join(root, '.preview', 'counter-browser-' + Date.now());
fs.mkdirSync(evidence, {recursive: true});

(async () => {
  const backend = spawn(process.env.PYTHON || 'python', [path.join(root, 'server', 'counter.py'), '--directory', path.join(evidence, 'counter-data'), '--port', '0']);
  let browser;
  try {
    const port = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(Error('Backend did not start')), 10000);
      backend.stdout.on('data', chunk => {
        const match = String(chunk).match(/loopback port (\d+)/);
        if (match) { clearTimeout(timeout); resolve(Number(match[1])); }
      });
      backend.once('exit', code => reject(Error('Backend exited ' + code)));
    });
    browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE || undefined});
    const context = await browser.newContext({userAgent: 'Mozilla/5.0 Workshop Browser Validation'});
    let mode = 'live';
    const failures = [];
    const reports = [];
    await context.route('https://t24085.github.io/patch-vigilantes/**', async route => {
      const pathname = new URL(route.request().url()).pathname.replace('/patch-vigilantes/', '');
      const file = path.join(root, 'site', pathname || 'index.html');
      let body = fs.readFileSync(file);
      const type = file.endsWith('.html') ? 'text/html' : file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : file.endsWith('.png') ? 'image/png' : 'image/webp';
      if (file.endsWith('.html') && mode !== 'disabled') body = Buffer.from(body.toString().replace('name="counter-endpoint" content=""', 'name="counter-endpoint" content="https://counter.test/counter"'));
      await route.fulfill({status: 200, contentType: type, body});
    });
    await context.route('https://counter.test/counter', async route => {
      if (mode === 'offline') return route.abort('failed');
      const headers = {'Access-Control-Allow-Origin': 'https://t24085.github.io', 'Cache-Control': 'no-store'};
      if (mode === 'large') return route.fulfill({status: 200, headers, json: {pageViews: Number.MAX_SAFE_INTEGER}});
      if (mode === 'invalid') return route.fulfill({status: 200, headers, json: {pageViews: 'bogus'}});
      if (mode === 'timeout') return new Promise(resolve => setTimeout(async () => {await route.abort().catch(() => {}); resolve();}, 6500));
      const request = route.request();
      const body = request.postData() || '';
      const result = await new Promise((resolve, reject) => {
        const proxy = http.request({host: '127.0.0.1', port, path: '/counter', method: request.method(), headers: {
          'Origin': 'https://t24085.github.io', 'User-Agent': 'Mozilla/5.0 Workshop Browser Validation',
          ...(body ? {'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body)} : {})
        }}, response => {
          const chunks = [];
          response.on('data', chunk => chunks.push(chunk));
          response.on('end', () => resolve({status: response.statusCode, headers: response.headers, body: Buffer.concat(chunks)}));
        });
        proxy.on('error', reject);
        proxy.end(body);
      });
      await route.fulfill(result);
    });
    const page = await context.newPage();
    page.on('pageerror', error => failures.push(error.message));
    async function visit(width, expected) {
      await page.setViewportSize({width, height: 900});
      await page.goto('https://t24085.github.io/patch-vigilantes/');
      await page.waitForFunction(() => /recorded|Try another visit|Counter unavailable\.$/.test(document.querySelector('#counter-status').textContent));
      if (expected) await page.waitForFunction(text => document.querySelector('#counter-status').textContent === text, expected);
      const layout = await page.evaluate(() => {
        const counter = document.querySelector('#visit-counter').getBoundingClientRect();
        const digits = document.querySelector('#counter-digits').getBoundingClientRect();
        return {width: innerWidth, scrollWidth: document.documentElement.scrollWidth, counterRight: counter.right, digitsRight: digits.right, digits: document.querySelector('#counter-digits').textContent, status: document.querySelector('#counter-status').textContent};
      });
      assert.ok(layout.scrollWidth <= width, JSON.stringify(layout));
      assert.ok(layout.digitsRight <= width, JSON.stringify(layout));
      reports.push({mode, ...layout});
      await page.locator('#visit-counter').screenshot({path: path.join(evidence, mode + '-' + width + '.png')});
      return layout;
    }
    await visit(1440, '1 page view recorded.');
    await visit(390, '1 page view recorded.');
    await visit(320, '1 page view recorded.');
    await visit(768, '1 page view recorded.');
    assert.equal((await context.cookies()).length, 0);
    // Expire the tab's short event so the next page load counts again.
    await page.evaluate(() => {const e = JSON.parse(sessionStorage.getItem('workshop-page-event')); e.created -= 31000; sessionStorage.setItem('workshop-page-event', JSON.stringify(e));});
    await visit(390, '2 page views recorded.');
    mode = 'large';
    await visit(320, '9,007,199,254,740,991 page views recorded.');
    mode = 'offline';
    assert.equal((await visit(390, 'Counter unavailable. Try another visit.')).digits, '------');
    mode = 'invalid';
    assert.equal((await visit(390, 'Counter unavailable. Try another visit.')).digits, '------');
    mode = 'disabled';
    assert.equal((await visit(320, 'Counter unavailable.')).digits, '------');
    mode = 'timeout';
    await visit(390, 'Counter unavailable. Try another visit.');
    assert.deepEqual(failures, []);
    fs.writeFileSync(path.join(evidence, 'report.json'), JSON.stringify({fixtureOnly: true, testCountsExcludedFromProduction: true, pageErrors: failures, reports}, null, 2));
    console.log(JSON.stringify({passed: reports.length, evidence, pageErrors: failures}));
  } finally {
    if (browser) await browser.close();
    backend.kill();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
