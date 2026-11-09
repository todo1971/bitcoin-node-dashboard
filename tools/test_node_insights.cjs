// Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
// SPDX-License-Identifier: GPL-3.0-only
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true, channel:process.env.QA_BROWSER || undefined});
  try {
    const page = await browser.newPage({timezoneId:'Europe/Berlin'});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const now = Math.floor(Date.now()/1000);
    await page.route('http://dashboard.test/**', async route => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname === '/api/protocol-history') {
        const fields = value => Object.fromEntries(['received','sent'].flatMap(direction=>['blocks','transactions','announcements','headers','other'].map((group,i)=>[`${group}_${direction}`,value==null?null:value*(i+1)])));
        return route.fulfill({json:{bucket_seconds:60,
          message_totals:{...fields(1000000000),measured_seconds:180},
          message_points:[{timestamp:now-180,...fields(1000)},{timestamp:now-120,...fields(2000)},{timestamp:now-60,...fields(null)},{timestamp:now,...fields(1500)}],
          block_points:[{timestamp:now-120,height:900001,fee_p10:1,fee_p25:2,fee_p50:3,fee_p75:4,fee_p90:5,fullness_percent:50},
                        {timestamp:now-60,height:900002,fee_p10:2,fee_p25:3,fee_p50:4,fee_p75:5,fee_p90:6,fullness_percent:100}],
        }});
      }
      if (pathname === '/api/traffic') {
        assert.equal(new URL(route.request().url()).searchParams.get('timezone'), 'Europe/Berlin');
        return route.fulfill({json:{
          timezone:'Europe/Berlin', bucket_seconds:60,
          periods:{selected:{received_bytes:1048576,sent_bytes:null,measured_seconds:600,window_seconds:3600}},
          daily:[{day_start:now-3600,received_bytes:999000000,sent_bytes:1000000000,mean_connections:98,
            peak_sent_bytes_per_second:8192,measured_seconds:1800,window_seconds:3600,
            start_local:'2026-11-07T10:00:00+01:00',end_local:'2026-11-07T11:00:00+01:00',
            networks:{ipv4_in:70,ipv4_out:2,ipv6_in:20,ipv6_out:3,onion_in:0,onion_out:3},
            blocks:{recorded_blocks:2,transactions:300,mean_block_size:1500000,total_fee_btc:null}}],
          weekly:{
            current:{start:now-7*86400,end:now,received_bytes:1000000000,sent_bytes:2000000000,
              mean_daily_sent_bytes:2000000000/7,measured_seconds:604800,window_seconds:604800},
            previous:{start:now-14*86400,end:now-7*86400,received_bytes:1000000000,sent_bytes:1000000000,
              mean_daily_sent_bytes:1000000000/7,measured_seconds:604800,window_seconds:604800},
            upload_change_percent:100,
          },
          network_points:[
            {timestamp:now-60,ipv4_in:70,ipv4_out:2,ipv6_in:20,ipv6_out:3,onion_in:0,onion_out:3},
            {timestamp:now,ipv4_in:71,ipv4_out:2,ipv6_in:20,ipv6_out:3,onion_in:0,onion_out:3},
          ],
          points:[
            {timestamp:now-120,received_bytes_per_second:2048,sent_bytes_per_second:1024,peak_sent_bytes_per_second:8192},
            {timestamp:now-60,received_bytes_per_second:null,sent_bytes_per_second:null,peak_sent_bytes_per_second:null},
            {timestamp:now,received_bytes_per_second:1024,sent_bytes_per_second:0,peak_sent_bytes_per_second:0},
          ],
        }});
      }
      if (pathname === '/api/recent-blocks') return route.fulfill({json:{blocks:[{height:900001,block_time:now,transactions:42,total_size:1048576,total_fee_btc:0.001}]}});
      const file = pathname === '/' ? 'index.html' : pathname.startsWith('/static/') ? pathname.slice(8) : null;
      if (file && fs.existsSync(path.join(__dirname,'../static',file))) return route.fulfill({body:fs.readFileSync(path.join(__dirname,'../static',file)),headers:{'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self'"},contentType:file.endsWith('.html')?'text/html':file.endsWith('.js')?'text/javascript':'application/json'});
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
      await page.locator('#messageTrafficDetails summary').click();
      await page.waitForFunction(()=>document.querySelector('#messageGroupRows').textContent.includes('GB'));
      assert.equal(await page.locator('#messageTrafficDetails summary').textContent(),catalog['Traffic nach Nachrichtentyp']);
      await page.waitForFunction(()=>{
        const canvas=document.querySelector('#messageReceivedChart');
        const rgba=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
        return rgba.some((red,i)=>i%4===0&&red===247&&rgba[i+1]===147&&rgba[i+2]===26);
      });
      assert.equal(await page.locator('#clientRows img').count(), 0);
      assert.match(await page.locator('#clientRows').textContent(), /<img/);
      await page.evaluate(() => window.dispatchEvent(new Event('node-offline')));
      assert.equal(await page.locator('#receiveRate').textContent(), '–');
      await page.click('#tab-history');
      await page.waitForFunction(() => document.querySelector('#trafficDailyRows').textContent.includes('GB'));
      assert.equal(await page.locator('#trafficRows').count(), 0);
      assert.equal(await page.locator('#trafficDailyTitle').textContent(), catalog['Bitcoin-Core-Traffic nach Tagen']);
      const dailyCells = await page.locator('#trafficDailyRows td').allTextContents();
      assert.deepEqual(dailyCells.slice(1), ['999 MB', '1 GB', '98', '8', '50 %']);
      assert.deepEqual(await page.evaluate(() => [0, null, 999999999, 2500000000].map(I18n.formatBytes)), [
        '0 B', '–', '1 GB', await page.evaluate(() => `${new Intl.NumberFormat(I18n.locale).format(2.5)} GB`),
      ]);
      assert.equal(await page.locator('#trafficTimezone').textContent(), 'Europe/Berlin');
      assert.equal(await page.locator('#weeklyTrafficChange').textContent(), '+100 %');
      const downloadPromise = page.waitForEvent('download');
      await page.locator('#exportDailyReport').click();
      const download = await downloadPromise;
      assert.equal(download.suggestedFilename(), 'bitcoin-core-24h.csv');
      const csv = fs.readFileSync(await download.path(), 'utf8');
      assert(csv.startsWith('\ufeff"local_date","timezone","start_local","end_local"'));
      assert(csv.includes('"2026-11-07T10:00:00+01:00"'));
      assert(csv.includes('"999000000","1000000000","98","8192"'));
      assert(csv.trimEnd().endsWith('"2","300","1500000",""'));
      await page.locator('#networkHistory summary').click();
      await page.waitForFunction(() => {
        const canvas = document.querySelector('#ipv4HistoryChart');
        const rgba = canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
        return rgba.some((red, i) => i % 4 === 0 && red === 247 && rgba[i+1] === 147 && rgba[i+2] === 26);
      });
      await page.waitForFunction(() => {
        const canvas = document.querySelector('#trafficChart');
        const rgba = canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
        return rgba.some((red, i) => i % 4 === 0 && red === 210 && rgba[i+1] === 168 && rgba[i+2] === 255);
      });
      await page.click('[data-range="1h"]');
      await page.click('#tab-analysis');
      await page.waitForFunction(() => document.querySelector('#recentBlockRows').textContent.includes('42'));
      assert.equal(await page.locator('#blockVisualDetails summary').textContent(),catalog['Gebührenband und Blockauslastung']);
      await page.waitForFunction(()=>{
        const canvas=document.querySelector('#confirmedFeeChart');
        const rgba=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
        return rgba.some((red,i)=>i%4===0&&red===247&&rgba[i+1]===147&&rgba[i+2]===26);
      });
      await page.waitForFunction(()=>{
        const canvas=document.querySelector('#blockFullnessChart');
        const rgba=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
        return rgba.some((red,i)=>i%4===0&&red===210&&rgba[i+1]===168&&rgba[i+2]===255);
      });
      await page.locator('#dailyBlockStats summary').click();
      assert.match(await page.locator('#dailyBlockRows').textContent(), /300/);
      assert.match(await page.locator('#dailyBlockRows').textContent(), /–/);
      await page.setViewportSize({width:390,height:844});
      for (const tab of ['network','history','analysis']) {
        await page.click('#tab-'+tab);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1), language+' '+tab+' overflow');
      }
      await page.setViewportSize({width:1280,height:800});
      if (language === 'en' && process.env.QA_SCREENSHOT) {
        await page.screenshot({path:process.env.QA_SCREENSHOT.replace('.png','-analysis.png'),fullPage:true});
        await page.click('#tab-network');
        await page.locator('#networkPanel summary').first().click();
        await page.screenshot({path:process.env.QA_SCREENSHOT,fullPage:true});
      }
    }
    assert.deepEqual(errors, []);
    console.log('Node insights browser QA passed: six languages, rates, unknown values, safe text, tabs and mobile layout.');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
