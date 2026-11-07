// Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
// SPDX-License-Identifier: GPL-3.0-only
(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const number = value => value == null ? '–' : new Intl.NumberFormat(I18n.locale, {maximumFractionDigits: 2}).format(value);
  const size = value => I18n.formatBytes(value);
  function card(panel, html) {
    const article = document.createElement('article');
    article.className = 'card full';
    article.innerHTML = html; // Fixed local templates only. RPC values use textContent.
    el(panel).querySelector('.grid').append(article);
  }
  card('networkPanel', `<div class="label">Verkehrsraten</div><dl><dt>Empfangen</dt><dd id="receiveRate">–</dd><dt>Gesendet</dt><dd id="sendRate">–</dd></dl><div class="sub">KiB/s · Mittelwert zwischen zwei Abfragen; bei Neustart oder Messlücke unbekannt.</div>`);
  card('networkPanel', `<details><summary>Peer-Software und Fähigkeiten</summary><p class="sub">Gemeldete Service-Flags sind Fähigkeiten, kein Nachweis ihrer Nutzung. Clientangaben sind Selbstauskünfte.</p><div class="table-scroll"><table class="data-table"><thead><tr><th>Client / Version</th><th>Peers</th></tr></thead><tbody id="clientRows"></tbody></table></div><div class="table-scroll"><table class="data-table"><thead><tr><th>Service-Flag</th><th>Peers</th></tr></thead><tbody id="serviceRows"></tbody></table></div><div class="table-scroll"><table class="data-table"><thead><tr><th>Verbindungsart</th><th>Peers</th></tr></thead><tbody id="connectionRows"></tbody></table></div><p class="sub">NETWORK: vollständige Blockhistorie · NETWORK_LIMITED: letzte Blöcke · WITNESS: SegWit · BLOOM: Bloom-Filter · COMPACT_FILTERS: kompakte Blockfilter · P2P_V2: verschlüsselter Transport unterstützt.</p></details>`);
  card('historyPanel', `
    <div class="label" id="trafficDailyTitle">Bitcoin-Core-Traffic nach Tagen</div>
    <p><button class="button" id="exportDailyReport" type="button" disabled>CSV-Bericht herunterladen</button></p>
    <div class="table-scroll"><table class="data-table">
      <thead><tr><th>Datum</th><th>Empfangen</th><th>Gesendet</th><th>Ø Verbindungen</th><th>Uploadspitze (KiB/s)</th><th>Messabdeckung</th></tr></thead>
      <tbody id="trafficDailyRows"></tbody>
    </table></div>
    <div class="sub" id="trafficState">Messwerte werden geladen …</div>
    <p class="sub">Zeitzone: <span id="trafficTimezone" data-no-i18n>–</span> · Uploadspitze: höchste Rate zwischen zwei Messpunkten.</p>
    <p class="sub">Die Tageswerte beziehen sich auf den gewählten Zeitraum. Messlücken, Neustarts und angebrochene Grenzintervalle fehlen in den Summen.</p>
    <div class="chart-box">
      <div class="legend" style="color:#d2a8ff">● Uploadspitze (KiB/s)</div>
      <canvas id="trafficChart"></canvas>
    </div>
    <details>
      <summary>Wochenvergleich</summary>
      <p class="sub">Sieben abgeschlossene Kalendertage im Vergleich zu den sieben Tagen davor. Die Änderung wird ab 90 % Messabdeckung in beiden Zeiträumen angezeigt.</p>
      <div class="table-scroll"><table class="data-table">
        <thead><tr><th>Zeitraum</th><th>Empfangen</th><th>Gesendet</th><th>Upload pro Tag</th><th>Stärkster Uploadtag</th><th>Messabdeckung</th></tr></thead>
        <tbody id="weeklyTrafficRows"></tbody>
      </table></div>
      <p class="sub"><span>Uploadänderung zur Vorwoche</span> <strong id="weeklyTrafficChange">–</strong></p>
    </details>`);
  card('historyPanel', `<details id="networkHistory"><summary>Netzwerkverlauf</summary>
    <div class="charts">
      <div class="chart-box"><b>IPv4</b><canvas id="ipv4HistoryChart"></canvas></div>
      <div class="chart-box"><b>IPv6</b><canvas id="ipv6HistoryChart"></canvas></div>
      <div class="chart-box"><b>Tor</b><canvas id="onionHistoryChart"></canvas></div>
    </div>
    <p class="legend"><span style="color:#f7931a">● In</span> · <span style="color:#58a6ff">● Out</span></p>
    <p class="sub">Mittlere Peer-Anzahl je Zeitabschnitt. Die getrennte Erfassung beginnt mit Version 1.23.0. Ältere Werte bleiben unbekannt.</p>
  </details>`);
  card('analysisPanel', `<details id="dailyBlockStats"><summary>Tägliche Blockstatistik</summary>
    <div class="table-scroll"><table class="data-table">
      <thead><tr><th>Datum</th><th>Erfasste Blöcke</th><th>Transaktionen</th><th>Ø Blockgröße</th><th>Gebühren (BTC)</th></tr></thead>
      <tbody id="dailyBlockRows"></tbody>
    </table></div>
    <p class="sub">Aus lokal erfassten Blöcken im gewählten Zeitraum. Bei fehlenden Einzelwerten bleibt die betreffende Tagesstatistik unbekannt.</p>
  </details>`);
  card('analysisPanel', `<div class="label">Letzte 20 erfasste Blöcke</div><div class="table-scroll"><table class="data-table"><thead><tr><th>Höhe</th><th>Blockzeit</th><th>Transaktionen</th><th>Größe</th><th>Gebühren</th></tr></thead><tbody id="recentBlockRows"></tbody></table></div><p class="sub">Lokal gespeicherte Blockstatistiken; keine vollständige oder unveränderliche Reorg-Chronik. Fehlende Blöcke können nachgetragen werden.</p>`);
  function rows(id, values, columns) {
    const body = el(id);
    body.replaceChildren();
    if (!values.length) values = [[I18n.text('Noch keine Messung vorhanden.'), ...Array(columns - 1).fill('–')]];
    for (const valuesRow of values) {
      const row = document.createElement('tr');
      for (const value of valuesRow) {
        const cell = document.createElement('td');
        cell.textContent = value;
        cell.style.overflowWrap = 'anywhere';
        row.append(cell);
      }
      body.append(row);
    }
  }
  let latest = null, traffic = null, blocks = [], selectedRange = historyRange;
  const typeNames = {'inbound':'In', 'outbound-full-relay':'Out · Full relay', 'block-relay-only':'Out · Block relay', manual:'Manuell', feeler:'Feeler', 'addr-fetch':'Adressabfrage', other:'Weitere'};
  const label = value => I18n.text(value);
  function renderPeers() {
    const data = latest?.network?.peer_analysis;
    const rates = latest?.network?.traffic;
    el('receiveRate').textContent = rates?.available ? number(rates.received_bytes_per_second / 1024) : '–';
    el('sendRate').textContent = rates?.available ? number(rates.sent_bytes_per_second / 1024) : '–';
    const clients = (data?.clients || []).map(item => [item.name === 'unknown' ? label('Unbekannt') : item.name, number(item.count)]);
    if (data?.other_clients) clients.push([label('Weitere'), number(data.other_clients)]);
    rows('clientRows', clients, 2);
    const services = (data?.services || []).map(item => [item.name === 'OTHER' ? label('Weitere') : item.name, number(item.count)]);
    if (data?.services_unknown) services.push([label('Unbekannt'), number(data.services_unknown)]);
    rows('serviceRows', services, 2);
    rows('connectionRows', (data?.connection_types || []).map(item => [label(typeNames[item.name] || 'Weitere'), number(item.count)]), 2);
  }
  function renderTraffic() {
    const timezone = traffic?.timezone || 'UTC';
    const coverage = value => value.window_seconds > 0 ? `${number(100 * value.measured_seconds / value.window_seconds)} %` : '–';
    const date = new Intl.DateTimeFormat(I18n.locale, {dateStyle:'medium', timeZone:timezone});
    const daily = traffic?.daily || [];
    const kib = value => value == null ? null : value / 1024;
    el('trafficTimezone').textContent = traffic?.timezone || '–';
    el('exportDailyReport').disabled = !daily.length;
    rows('trafficDailyRows', daily.map(value => [
      date.format(value.day_start * 1000), size(value.received_bytes), size(value.sent_bytes),
      number(value.mean_connections), number(kib(value.peak_sent_bytes_per_second)),
      coverage(value),
    ]), 6);
    const weekly = traffic?.weekly;
    rows('weeklyTrafficRows', ['current', 'previous'].map(key => {
      const week = weekly?.[key];
      if (!week) return [label('Noch keine Messung vorhanden.'), '–', '–', '–', '–', '–'];
      const strongest = week.strongest_day;
      return [`${date.format(week.start * 1000)} – ${date.format((week.end - 1) * 1000)}`,
        size(week.received_bytes), size(week.sent_bytes), size(week.mean_daily_sent_bytes),
        strongest ? `${date.format(strongest.day_start * 1000)} · ${size(strongest.sent_bytes)}` : '–',
        coverage(week)];
    }), 6);
    el('weeklyTrafficChange').textContent = weekly?.upload_change_percent == null ? '–' :
      `${weekly.upload_change_percent > 0 ? '+' : ''}${number(weekly.upload_change_percent)} %`;
    rows('dailyBlockRows', daily.map(value => {
      const block = value.blocks || {};
      return [date.format(value.day_start * 1000), number(block.recorded_blocks),
        number(block.transactions), size(block.mean_block_size),
        block.total_fee_btc == null ? '–' : new Intl.NumberFormat(I18n.locale, {maximumFractionDigits:8}).format(block.total_fee_btc)];
    }), 5);
    if (!el('historyPanel').hidden) {
      const points = [...daily].reverse().map(value => ({
        timestamp:value.day_start, peak:kib(value.peak_sent_bytes_per_second),
      }));
      drawChart(el('trafficChart'), points, [
        {key:'peak',color:'#d2a8ff',dash:[4,4],markers:true},
      ], 86400, {timeZone:timezone, calendarDays:true});
      renderNetworkHistory();
    }
  }
  function renderNetworkHistory() {
    if (el('historyPanel').hidden || !el('networkHistory').open) return;
    for (const network of ['ipv4', 'ipv6', 'onion']) {
      drawChart(el(`${network}HistoryChart`), traffic?.network_points || [], [
        {key:`${network}_in`,color:'#f7931a'},
        {key:`${network}_out`,color:'#58a6ff'},
      ], traffic?.bucket_seconds || 300, {timeZone:traffic?.timezone || 'UTC'});
    }
  }
  function exportReport() {
    if (!traffic?.daily?.length) return;
    const columns = ['local_date','timezone','start_local','end_local','received_bytes','sent_bytes',
      'mean_connections','peak_sent_bytes_per_second','measured_seconds','window_seconds',
      'ipv4_in','ipv4_out','ipv6_in','ipv6_out','onion_in','onion_out',
      'recorded_blocks','transactions','mean_block_size_bytes','total_fee_btc'];
    const lines = [columns, ...traffic.daily.map(day => [
      day.start_local.slice(0,10), traffic.timezone,
      day.start_local, day.end_local,
      day.received_bytes, day.sent_bytes, day.mean_connections, day.peak_sent_bytes_per_second,
      day.measured_seconds, day.window_seconds,
      ...['ipv4_in','ipv4_out','ipv6_in','ipv6_out','onion_in','onion_out'].map(key => day.networks?.[key]),
      day.blocks?.recorded_blocks, day.blocks?.transactions, day.blocks?.mean_block_size, day.blocks?.total_fee_btc,
    ])];
    const csv = lines.map(line => line.map(value => `"${String(value ?? '').replaceAll('"','""')}"`).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\ufeff', csv], {type:'text/csv;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = `bitcoin-core-${selectedRange}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function renderBlocks() {
    rows('recentBlockRows', blocks.map(block => [number(block.height), block.block_time == null ? '–' : new Date(block.block_time * 1000).toLocaleString(I18n.locale), number(block.transactions), size(block.total_size), block.total_fee_btc == null ? '–' : `${new Intl.NumberFormat(I18n.locale, {minimumFractionDigits:8, maximumFractionDigits:8}).format(block.total_fee_btc)} BTC`]), 5);
  }
  async function loadTraffic() {
    const range = selectedRange;
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
      const query = new URLSearchParams({range, timezone});
      const response = await fetch(`/api/traffic?${query}`, {cache:'no-store'});
      if (!response.ok) throw Error();
      const data = await response.json();
      if (range !== selectedRange) return;
      traffic = data;
      el('trafficState').textContent = label('Gemessene Daten; fehlende Abdeckung bleibt unbekannt.');
    } catch {
      if (range !== selectedRange) return;
      traffic = null;
      el('trafficState').textContent = label('Verkehrsdaten nicht verfügbar.');
    }
    renderTraffic();
  }
  async function loadBlocks() {
    try {
      const response = await fetch('/api/recent-blocks', {cache:'no-store'});
      if (!response.ok) throw Error();
      blocks = (await response.json()).blocks || [];
    } catch { blocks = []; }
    renderBlocks();
  }
  window.addEventListener('node-snapshot', event => {latest = event.detail; renderPeers();});
  window.addEventListener('node-offline', () => {latest = null; renderPeers();});
  window.addEventListener('history-range', () => {selectedRange = historyRange; traffic = null; renderTraffic(); loadTraffic();});
  window.addEventListener('dashboard-view', () => requestAnimationFrame(renderTraffic));
  window.addEventListener('resize', () => requestAnimationFrame(renderTraffic));
  window.addEventListener('language-ready', () => {renderPeers(); renderTraffic(); renderBlocks();});
  el('networkHistory').addEventListener('toggle', renderNetworkHistory);
  el('exportDailyReport').addEventListener('click', exportReport);
  latest = window.__nodeSnapshot || null;
  renderPeers(); loadTraffic(); loadBlocks();
  setInterval(() => {if (!document.hidden) {loadTraffic(); loadBlocks();}}, 60000);
})();
