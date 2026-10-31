// Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
// SPDX-License-Identifier: GPL-3.0-only
// Optional browser QA: requires Playwright and an installed Chromium browser.
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true, channel:process.env.QA_BROWSER || undefined});
  try {
    const page = await browser.newPage();
    await page.route('http://dashboard.test/**', async route => {
      const pathname = new URL(route.request().url()).pathname;
      const files = {'/':'index.html','/admin':'admin.html','/static/i18n.js':'i18n.js','/static/locales/en.json':'locales/en.json'};
      if (files[pathname]) {
        const file = files[pathname];
        await route.fulfill({body:fs.readFileSync(path.join(__dirname,'../static',file)),contentType:file.endsWith('.html')?'text/html':file.endsWith('.js')?'text/javascript':'application/json'});
      } else await route.fulfill({status:503,json:{error:'QA offline'}});
    });
    await page.goto('http://dashboard.test/');
    await page.waitForSelector('select');
    assert.equal(await page.locator('#tab-overview').textContent(), 'Überblick');
    await page.selectOption('select', 'en');
    await page.waitForFunction(() => document.querySelector('#tab-overview').textContent === 'Overview');
    assert.equal(await page.locator('html').getAttribute('lang'),'en');
    await page.evaluate(() => {
      document.getElementById('syncText').textContent='99.9 % synchronisiert';
      const note=document.createElement('p'); note.id='qa-note';note.textContent='UTFXO_Netzwerk 2 aktive Alarme';document.body.append(note);
    });
    await page.waitForFunction(() => document.querySelector('#syncText').textContent === '99.9 % synchronized');
    assert.equal(await page.locator('#qa-note').textContent(), 'UTFXO_Netzwerk 2 active alerts');
    await page.goto('http://dashboard.test/admin');
    await page.waitForFunction(() => document.querySelector('#configHeading').textContent === 'Dashboard configuration');
    await page.evaluate(() => {
      document.getElementById('updateLog').textContent='Netzwerk Fehler';
      const input=document.createElement('input'); input.value='Netzwerk';input.placeholder='Nicht gesetzt';input.id='qa-input';document.body.append(input);
    });
    await page.waitForTimeout(100);
    assert.equal(await page.locator('#updateLog').textContent(), 'Netzwerk Fehler');
    assert.equal(await page.locator('#qa-input').inputValue(), 'Netzwerk');
    assert.equal(await page.locator('#qa-input').getAttribute('placeholder'), 'Not configured');
    await page.selectOption('select','de');
    await page.waitForFunction(() => document.querySelector('#configHeading').textContent === 'Dashboard-Konfiguration');
    console.log('Language browser QA passed: selection, persistence, live updates, boundaries, original logs and form values.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1});
