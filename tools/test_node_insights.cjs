// Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
// SPDX-License-Identifier: GPL-3.0-only
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true, channel:process.env.QA_BROWSER || undefined});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const now = Math.floor(Date.now()/1000);
    await page.route('http://dashboard.test/**', async route => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname === '/api/traffic') return route.fulfill({json:{periods:{selected:{received_bytes:1048576,sent_bytes:null,measured_seconds:600,window_seconds:3600}},points:[{timestamp:now-120,received_bytes_per_second:2048,sent_bytes_per_second:1024},{timestamp:now-60,received_bytes_per_second:null,sent_bytes_per_second:null},{timestamp:now,received_bytes_per_second:1024,sent_bytes_per_second:0}]}});
      if (pathname === '/api/recent-blocks') return route.fulfill({json:{blocks:[{height:900001,block_time:now,transactions:42,total_size:1048576,total_fee_btc:0.001}]}});
      const file = pathname === '/' ? 'index.html' : pathname.startsWith('/static/') ? pathname.slice(8) : null;
      if (file && fs.existsSync(path.join(__dirname,'../static',file))) return route.fulfill({body:fs.readFileSync(path.join(__dirname,'../static',file)),contentType:file.endsWith('.html')?'text/html':file.endsWith('.js')?'text/javascript':'application/json'});
      return route.fulfill({status:503,json:{error:'Offline for QA'}});
    });
    for (const language of ['de','en','es','pt-BR','zh-Hans','ru']) {
      await page.goto('http://dashboard.test/#network');
      await page.selectOption('select', language);
      const catalog = JSON.parse(fs.readFileSync(path.join(__dirname,'../static/locales',language+'.json')));
      await page.waitForFunction(text => document.querySelector('summary')?.textContent === text, catalog['Peer-Software und Fähigkeiten']);
      await page.evaluate(() => window.dispatchEvent(new CustomEvent('node-snapshot',{detail:{network:{traffic:{available:true,received_bytes_per_second:2048,sent_bytes_per_second:0},peer_analysis:{clients:[{name:'<img src=x onerror=alert(1)>',count:2}],services:[{name:'WITNESS',count:2}],connection_types:[{name:'inbound',count:2}]}}}})));
      assert.equal(await page.locator('#receiveRate').textContent(), '2');
      assert.equal(await page.locator('#sendRate').textContent(), '0');
      assert.equal(await page.locator('#clientRows img').count(), 0);
      assert.match(await page.locator('#clientRows').textContent(), /<img/);
      await page.evaluate(() => window.dispatchEvent(new Event('node-offline')));
      assert.equal(await page.locator('#receiveRate').textContent(), '–');
      await page.click('#tab-history');
      await page.waitForFunction(() => document.querySelector('#trafficRows').textContent.includes('MiB'));
      assert.match(await page.locator('#trafficRows').textContent(), /–/);
      await page.click('[data-range="1h"]');
      await page.click('#tab-analysis');
      await page.waitForFunction(() => document.querySelector('#recentBlockRows').textContent.includes('42'));
      await page.setViewportSize({width:390,height:844});
      for (const tab of ['network','history','analysis']) {
        await page.click('#tab-'+tab);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1), language+' '+tab+' overflow');
      }
      await page.setViewportSize({width:1280,height:800});
      if (language === 'en' && process.env.QA_SCREENSHOT) {
        await page.click('#tab-network');
        await page.locator('summary').click();
        await page.screenshot({path:process.env.QA_SCREENSHOT,fullPage:true});
      }
    }
    assert.deepEqual(errors, []);
    console.log('Node insights browser QA passed: six languages, rates, unknown values, safe text, tabs and mobile layout.');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
