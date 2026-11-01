// Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
// SPDX-License-Identifier: GPL-3.0-only
(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const number = value => value == null ? '–' : new Intl.NumberFormat(I18n.locale, {maximumFractionDigits: 2}).format(value);
  const size = value => value == null ? '–' : `${number(value / 1048576)} MiB`;
  function card(panel, html) {
    const article = document.createElement('article');
    article.className = 'card full';
    article.innerHTML = html; // Fixed local templates only. RPC values use textContent.
    el(panel).querySelector('.grid').append(article);
  }
  card('networkPanel', `<div class="label">Verkehrsraten</div><dl><dt>Empfangen</dt><dd id="receiveRate">–</dd><dt>Gesendet</dt><dd id="sendRate">–</dd></dl><div class="sub">KiB/s · Mittelwert zwischen zwei Abfragen; bei Neustart oder Messlücke unbekannt.</div>`);
  card('networkPanel', `<details><summary>Peer-Software und Fähigkeiten</summary><p class="sub">Gemeldete Service-Flags sind Fähigkeiten, kein Nachweis ihrer Nutzung. Clientangaben sind Selbstauskünfte.</p><div class="table-scroll"><table class="data-table"><thead><tr><th>Client / Version</th><th>Peers</th></tr></thead><tbody id="clientRows"></tbody></table></div><div class="table-scroll"><table class="data-table"><thead><tr><th>Service-Flag</th><th>Peers</th></tr></thead><tbody id="serviceRows"></tbody></table></div><div class="table-scroll"><table class="data-table"><thead><tr><th>Verbindungsart</th><th>Peers</th></tr></thead><tbody id="connectionRows"></tbody></table></div><p class="sub">NETWORK: vollständige Blockhistorie · NETWORK_LIMITED: letzte Blöcke · WITNESS: SegWit · BLOOM: Bloom-Filter · COMPACT_FILTERS: kompakte Blockfilter · P2P_V2: verschlüsselter Transport unterstützt.</p></details>`);
  card('historyPanel', `<div class="label">Netzwerkverkehr im Zeitraum</div><div class="chart-box"><div class="legend">Empfangen / Gesendet · KiB/s</div><canvas id="trafficChart"></canvas></div><div class="table-scroll"><table class="data-table"><thead><tr><th>Zeitraum</th><th>Empfangen</th><th>Gesendet</th><th>Messabdeckung</th></tr></thead><tbody id="trafficRows"></tbody></table></div><div class="sub" id="trafficState">Messwerte werden geladen …</div><p class="sub">Nur gemessene Intervalle: Neustarts und Lücken fehlen in Summen. Tages- und Monatsgrenzen sind UTC; angebrochene Grenzintervalle werden ausgelassen.</p>`);
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
    const names = {selected:'Gewählter Zeitraum', today:'Heute (UTC)', month:'Dieser Monat (UTC)'};
    rows('trafficRows', Object.entries(traffic?.periods || {}).map(([key, value]) => [label(names[key]), size(value.received_bytes), size(value.sent_bytes), value.window_seconds > 0 ? `${number(100 * value.measured_seconds / value.window_seconds)} %` : '–']), 4);
    if (!el('historyPanel').hidden) {
      const points = (traffic?.points || []).map(point => ({...point, received:point.received_bytes_per_second == null ? null : point.received_bytes_per_second / 1024, sent:point.sent_bytes_per_second == null ? null : point.sent_bytes_per_second / 1024}));
      drawChart(el('trafficChart'), points, [{key:'received',color:'#f7931a'},{key:'sent',color:'#58a6ff'}], traffic?.bucket_seconds || 300);
    }
  }
  function renderBlocks() {
    rows('recentBlockRows', blocks.map(block => [number(block.height), block.block_time == null ? '–' : new Date(block.block_time * 1000).toLocaleString(I18n.locale), number(block.transactions), size(block.total_size), block.total_fee_btc == null ? '–' : `${new Intl.NumberFormat(I18n.locale, {minimumFractionDigits:8, maximumFractionDigits:8}).format(block.total_fee_btc)} BTC`]), 5);
  }
  async function loadTraffic() {
    const range = selectedRange;
    try {
      const response = await fetch(`/api/traffic?range=${encodeURIComponent(range)}`, {cache:'no-store'});
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
  latest = window.__nodeSnapshot || null;
  renderPeers(); loadTraffic(); loadBlocks();
  setInterval(() => {if (!document.hidden) {loadTraffic(); loadBlocks();}}, 60000);
})();
