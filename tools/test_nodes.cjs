// Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
// SPDX-License-Identifier: GPL-3.0-only
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({headless:true, channel:process.env.QA_BROWSER || undefined});
  try {
    const page = await browser.newPage();
    const requests = [], errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('http://dashboard.test/**', async route => {
      const url = new URL(route.request().url());
      requests.push(url.pathname);
      if (url.pathname === '/api/nodes') return route.fulfill({json:{nodes:[{id:'local',name:'Primary'},{id:'second',name:'Second <img src=x>'}]}});
      if (url.pathname === '/api/nodes/second/history') return route.fulfill({json:{source:'second'}});
      if (url.pathname === '/api/history') return route.fulfill({json:{source:'local'}});
      if (url.pathname.startsWith('/api/')) return route.fulfill({status:503,json:{error:'Selected node unavailable'}});
      const file = url.pathname === '/' ? 'index.html' : url.pathname.startsWith('/static/') ? url.pathname.slice(8) : null;
      if (file && fs.existsSync(path.join(__dirname,'../static',file))) {
        return route.fulfill({body:fs.readFileSync(path.join(__dirname,'../static',file)), contentType:file.endsWith('.html')?'text/html':file.endsWith('.js')?'text/javascript':'application/json'});
      }
      return route.fulfill({status:404,body:''});
    });
    await page.goto('http://dashboard.test/?node=second#history');
    await page.waitForFunction(() => document.querySelector('#nodeSelect').options.length === 2);
    assert.equal(await page.locator('#nodeSelect').inputValue(), 'second');
    assert.equal(await page.locator('#adminLink').isVisible(), false);
    assert.equal(await page.locator('#nodeSelect img').count(), 0);
    assert.equal(await page.evaluate(async () => (await (await fetch('/api/history?range=1h')).json()).source), 'second');
    assert(requests.includes('/api/nodes/second/events'));
    assert(!requests.includes('/api/dashboard'));
    assert.match(await page.locator('#status').textContent(), /nicht erreichbar/);
    assert.equal(await page.locator('#blocks').textContent(), '–');
    await page.selectOption('#nodeSelect', 'local');
    await page.waitForURL('http://dashboard.test/#history');
    assert.equal(await page.locator('#adminLink').isVisible(), true);
    assert.equal(await page.evaluate(async () => (await (await fetch('/api/history')).json()).source), 'local');
    requests.length = 0;
    await page.goto('http://dashboard.test/?node=missing');
    await page.waitForFunction(() => document.querySelector('#nodeSelect').value === 'missing');
    assert(!requests.includes('/api/dashboard'));
    assert(requests.includes('/api/nodes/missing/dashboard'));
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    assert.deepEqual(errors, []);
    console.log('Multi-node browser QA passed: selection, separate API and SSE routes, offline state, no local fallback, safe labels, mobile layout.');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
