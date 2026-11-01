// Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
// SPDX-License-Identifier: GPL-3.0-only
// Optional browser QA: requires Playwright and an installed Chromium browser.
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const languages = ['de', 'en', 'es', 'pt-BR', 'zh-Hans', 'ru'];
const catalog = Object.fromEntries(languages.map(lang => [lang, JSON.parse(fs.readFileSync(path.join(__dirname, '../static/locales', lang + '.json'), 'utf8'))]));
(async () => {
  const browser = await chromium.launch({headless:true, channel:process.env.QA_BROWSER || undefined});
  try {
    const page = await browser.newPage();
    let languageFailure = false, posts = 0;
    await page.route('http://dashboard.test/**', async route => {
      const pathname = new URL(route.request().url()).pathname;
      if (route.request().method() !== 'GET') { posts++; return route.fulfill({status:403,json:{error:'Unexpected mutation'}}); }
      if (pathname === '/api/admin/status') return route.fulfill({json:{dashboard:{available:true,current:'1.19.0',latest:'1.19.0'},bitcoin:'Bitcoin Core',updates_enabled:true,bitcoin_keyring_ready:true,bitcoin_upload:{filename:'bitcoin-31.1-x86_64-linux-gnu.tar.gz',size:100,sha256:'0'.repeat(64)}}});
      if (pathname === '/api/admin/config') return route.fulfill({json:{fields:[{key:'DASHBOARD_GITHUB_TOKEN',label:'GitHub-Token (leer lassen = unverändert)',section:'Updates',kind:'secret',value:'',configured:false}]}});
      const files = {'/':'index.html','/admin':'admin.html','/static/i18n.js':'i18n.js',...Object.fromEntries(languages.map(lang => ['/static/locales/' + lang + '.json','locales/' + lang + '.json']))};
      if (files[pathname] && !(languageFailure && pathname.endsWith('/ru.json'))) {
        const file = files[pathname];
        return route.fulfill({body:fs.readFileSync(path.join(__dirname,'../static',file)),contentType:file.endsWith('.html')?'text/html':file.endsWith('.js')?'text/javascript':'application/json'});
      }
      return route.fulfill({status:503,json:{error:'QA offline'}});
    });
    await page.goto('http://dashboard.test/#network');
    await page.waitForSelector('select');
    assert.equal(await page.locator('#tab-overview').textContent(), 'Überblick');
    assert.deepEqual(await page.locator('select option').evaluateAll(options => options.map(option => option.value)), languages);
    for (const language of languages) {
      const t = source => catalog[language][source];
      await page.selectOption('select', language);
      await page.waitForFunction(expected => document.querySelector('#tab-overview').textContent === expected, t('Überblick'));
      assert.equal(await page.locator('html').getAttribute('lang'), language);
      assert.equal(new URL(page.url()).hash, '#network');
      await page.evaluate(() => {
        document.getElementById('syncText').textContent = '99.9 % synchronisiert';
        document.getElementById('mode').textContent = 'Pruned Node';
        const note = document.createElement('p'); note.id = 'qa-note'; note.textContent = 'UTFXO_Netzwerk'; document.body.append(note);
      });
      await page.waitForFunction(expected => document.querySelector('#syncText').textContent === expected, '99.9 % ' + t('synchronisiert'));
      await page.waitForFunction(expected => document.querySelector('#mode').textContent === expected, t('Pruned Node'));
      assert.equal(await page.locator('#qa-note').textContent(), 'UTFXO_Netzwerk');
      const before = await page.locator('#tab-network').textContent();
      await page.waitForTimeout(60);
      assert.equal(await page.locator('#tab-network').textContent(), before, 'translation must be stable');
      await page.goto('http://dashboard.test/admin');
      await page.waitForFunction(expected => document.querySelector('#configHeading').textContent === expected, t('Dashboard-Konfiguration'));
      await page.waitForFunction(expected => document.querySelector('#configFields input')?.placeholder === expected, t('Nicht gesetzt'));
      assert.equal(await page.locator('select').inputValue(), language);
      await page.evaluate(() => {
        document.getElementById('updateLog').textContent = 'Netzwerk Fehler <b>raw</b>';
        document.querySelector('#configFields input').value = 'Netzwerk';
      });
      for (const [button, question] of [
        ['#dashboardUpdate', 'Dashboard jetzt aus dem neuesten verifizierten GitHub-Release aktualisieren?'],
        ['#coreUpdate', 'Bitcoin Core jetzt aus dem hochgeladenen und signaturgeprüften Archiv aktualisieren?'],
      ]) {
        const dialog = page.waitForEvent('dialog');
        const click = page.click(button);
        const prompt = await dialog;
        assert.equal(prompt.message(), t(question));
        await prompt.dismiss(); await click;
      }
      assert.equal(await page.locator('#updateLog').textContent(), 'Netzwerk Fehler <b>raw</b>');
      assert.equal(await page.locator('#configFields input').inputValue(), 'Netzwerk');
      assert.equal(await page.locator('#updateLog b').count(), 0);
      await page.goto('http://dashboard.test/#network');
      await page.waitForFunction(expected => document.querySelector('#tab-overview').textContent === expected, t('Überblick'));
      for (const viewport of [{width:1280,height:900},{width:390,height:844}]) {
        await page.setViewportSize(viewport);
        for (const view of ['overview','network','analysis','history','system']) {
          await page.evaluate(view => { location.hash = view; }, view);
          await page.waitForFunction(view => !document.getElementById(view + 'Panel').hidden, view);
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, language + ' ' + view + ' should not overflow');
        }
      }
      if (process.env.QA_SCREENSHOT_DIR && language !== 'de') {
        fs.mkdirSync(process.env.QA_SCREENSHOT_DIR,{recursive:true});
        await page.setViewportSize({width:1280,height:900});
        await page.evaluate(() => { location.hash='overview'; });
        await page.screenshot({path:path.join(process.env.QA_SCREENSHOT_DIR,language + '.png'),fullPage:true});
      }
      await page.setViewportSize({width:1280,height:900});
      await page.goto('http://dashboard.test/#network');
    }
    assert.equal(posts, 0);
    await page.evaluate(() => localStorage.setItem('dashboard-language','../../ja'));
    await page.reload(); await page.waitForSelector('select');
    assert.equal(await page.locator('html').getAttribute('lang'), 'de');
    languageFailure = true;
    await page.selectOption('select','ru');
    await page.waitForFunction(() => document.querySelector('html').lang === 'de' && document.body.textContent.includes('Не удалось загрузить язык.'));
    assert.equal(await page.locator('#tab-overview').textContent(), 'Überblick');
    console.log('Language browser QA passed for six languages: selection, persistence, live updates, confirmation dialogs, desktop/mobile tabs, protected logs and form values, invalid preferences and unavailable catalogs.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1});
