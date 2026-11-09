// Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
// SPDX-License-Identifier: GPL-3.0-only
(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const groups = [
    {key:'blocks',name:'Blöcke',color:'#f7931a'},
    {key:'transactions',name:'Transaktionen',color:'#58a6ff'},
    {key:'announcements',name:'Ankündigungen und Anfragen',color:'#37d67a'},
    {key:'headers',name:'Blockheader',color:'#d2a8ff'},
    {key:'other',name:'Weitere Nachrichten',color:'#ff6b6b'},
  ];
  function card(panel, html) {
    const article = document.createElement('article');
    article.className = 'card full';
    article.innerHTML = html; // Fixed local templates; values below use textContent.
    el(panel).querySelector('.grid').append(article);
  }
  card('networkPanel', `<details id="messageTrafficDetails"><summary>Traffic nach Nachrichtentyp</summary>
    <p class="sub">Erfasster P2P-Verkehr bestehender Verbindungen. Neue und getrennte Peers fehlen; Neustarts und Messlücken bleiben unbekannt. Kein vollständiger Provider-Traffic.</p>
    <div class="charts"><div class="chart-box"><b>Empfangen (KB/s)</b><canvas id="messageReceivedChart"></canvas></div>
    <div class="chart-box"><b>Gesendet (KB/s)</b><canvas id="messageSentChart"></canvas></div></div>
    <p class="legend" id="messageLegend"></p>
    <div class="table-scroll"><table class="data-table"><thead><tr><th>Nachrichtengruppe</th><th>Empfangen</th><th>Gesendet</th></tr></thead><tbody id="messageGroupRows"></tbody></table></div>
    <p class="sub" id="messageCaptureState">Noch keine Messung vorhanden.</p>
    <p class="sub">Ankündigungen und Anfragen können Blöcke und Transaktionen betreffen. Die Zuordnung erfolgt nach P2P-Nachrichtentyp, nicht nach Inhalt.</p>
  </details>`);
  card('analysisPanel', `<details id="blockVisualDetails" open><summary>Gebührenband und Blockauslastung</summary>
    <div class="charts"><div class="chart-box"><b>Bestätigte Gebührenraten (sat/vB)</b><canvas id="confirmedFeeChart"></canvas></div>
    <div class="chart-box"><b>Blockauslastung (%)</b><canvas id="blockFullnessChart"></canvas></div></div>
    <p class="legend"><span style="color:#58a6ff">● P10–P90</span> · <span style="color:#37d67a">● P25–P75</span> · <span style="color:#f7931a">● P50</span></p>
    <p class="sub">Perzentile sind nach Transaktionsgewicht gewichtet. P50 ist der Median; P10 und P90 begrenzen das äußere Gebührenband. Keine Vorhersage künftiger Gebühren.</p>
    <p class="sub">Blockauslastung: vollständiges Blockgewicht einschließlich Coinbase geteilt durch 4.000.000 WU. WU = Gewichtseinheiten; vB = virtuelle Bytes.</p>
    <p class="sub">Je Zeitabschnitt wird der letzte erfasste Block gezeigt; Perzentile werden nicht gemittelt. Ältere oder geprunte Daten können fehlen.</p>
    <p class="sub" id="blockVisualState">Noch keine Messung vorhanden.</p>
  </details>`);
  let data = null, generation = 0;
  const number = value => new Intl.NumberFormat(I18n.locale,{maximumFractionDigits:1}).format(value);
  function stacked(canvas, direction) {
    const points = data?.message_points || [];
    const scale = window.devicePixelRatio || 1;
    const w = Math.max(160,canvas.getBoundingClientRect().width), h = 220;
    canvas.width = w*scale; canvas.height = h*scale;
    const c = canvas.getContext('2d'); c.scale(scale,scale);
    const pad = {l:50,r:12,t:12,b:30};
    const sums = points.map(point => groups.every(group => point[`${group.key}_${direction}`]!=null) ?
      groups.reduce((sum,group)=>sum+Number(point[`${group.key}_${direction}`])/1000,0) : null);
    if (!sums.some(value=>value!=null)) {
      c.fillStyle='#9ba8b6';c.font='14px system-ui';c.textAlign='center';
      c.fillText(I18n.text('Noch nicht genügend Messwerte'),w/2,h/2);return;
    }
    const maximum = Math.max(1,...sums.filter(value=>value!=null));
    const first=points[0].timestamp,last=points.at(-1).timestamp;
    const x=i=>pad.l+(first===last?0.5:(points[i].timestamp-first)/(last-first))*(w-pad.l-pad.r);
    const y=value=>pad.t+(1-value/maximum)*(h-pad.t-pad.b);
    c.font='11px system-ui';c.textAlign='right';
    for(let i=0;i<=4;i++){
      const value=maximum*i/4,yy=y(value);c.strokeStyle='#29313a';c.beginPath();c.moveTo(pad.l,yy);c.lineTo(w-pad.r,yy);c.stroke();
      c.fillStyle='#9ba8b6';c.fillText(number(value),pad.l-6,yy+4);
    }
    let segments=[],segment=[];
    points.forEach((point,i)=>{
      if(sums[i]==null){if(segment.length)segments.push(segment);segment=[];return;}
      if(segment.length&&point.timestamp-points[segment.at(-1)].timestamp>(data.bucket_seconds||300)*1.5){segments.push(segment);segment=[];}
      segment.push(i);
    });
    if(segment.length)segments.push(segment);
    groups.forEach((group,layer)=>{
      const lower=i=>groups.slice(0,layer).reduce((sum,g)=>sum+Number(points[i][`${g.key}_${direction}`])/1000,0);
      const upper=i=>lower(i)+Number(points[i][`${group.key}_${direction}`])/1000;
      c.fillStyle=group.color;
      for(const segment of segments){
        if(segment.length===1){const i=segment[0];c.fillRect(x(i)-3,y(upper(i)),6,Math.max(0,y(lower(i))-y(upper(i))));continue;}
        c.beginPath();segment.forEach((i,j)=>j?c.lineTo(x(i),y(upper(i))):c.moveTo(x(i),y(upper(i))));
        [...segment].reverse().forEach(i=>c.lineTo(x(i),y(lower(i))));c.closePath();c.fill();
      }
    });
    c.textAlign='center';c.fillStyle='#9ba8b6';
    for(const i of new Set([0,Math.floor((points.length-1)/2),points.length-1])){
      const date=new Date(points[i].timestamp*1000);
      c.fillText(['1h','6h','12h','24h'].includes(historyRange)?date.toLocaleTimeString(I18n.locale,{hour:'2-digit',minute:'2-digit'}):date.toLocaleDateString(I18n.locale,{day:'2-digit',month:'2-digit'}),x(i),h-7);
    }
  }
  function render() {
    const rows=el('messageGroupRows');rows.replaceChildren();
    const legend=el('messageLegend');legend.replaceChildren();
    for(const group of groups){
      const row=document.createElement('tr');
      for(const value of [I18n.text(group.name),I18n.formatBytes(data?.message_totals?.[`${group.key}_received`]),I18n.formatBytes(data?.message_totals?.[`${group.key}_sent`])]){
        const cell=document.createElement('td');cell.textContent=value;row.append(cell);
      }
      rows.append(row);
      const item=document.createElement('span');item.style.color=group.color;item.style.marginRight='12px';item.style.display='inline-block';item.textContent=`● ${I18n.text(group.name)}`;legend.append(item);
    }
    el('messageCaptureState').textContent = data?.message_totals?.measured_seconds ?
      `${I18n.text('Messzeit mit vergleichbaren Peers')}: ${number(data.message_totals.measured_seconds/60)} min` : I18n.text('Noch keine vergleichbaren Peer-Messungen.');
    const points=data?.block_points||[];
    el('blockVisualState').textContent = points.some(point=>point.fee_p50!=null||point.fullness_percent!=null) ?
      `${I18n.text('Block-Messpunkte')}: ${number(points.length)}` : I18n.text('Neue Blockdaten werden ab dieser Version erfasst.');
    if(!el('networkPanel').hidden&&el('messageTrafficDetails').open){stacked(el('messageReceivedChart'),'received');stacked(el('messageSentChart'),'sent');}
    if(!el('analysisPanel').hidden&&el('blockVisualDetails').open){
      drawChart(el('confirmedFeeChart'),points,[
        {key:'fee_p10',color:'#58a6ff',markers:true},{key:'fee_p90',color:'#58a6ff',markers:true},
        {key:'fee_p25',color:'#37d67a',markers:true},{key:'fee_p75',color:'#37d67a',markers:true},
        {key:'fee_p50',color:'#f7931a',markers:true},
      ],data?.bucket_seconds||300,{minimum:0,bands:[{low:'fee_p10',high:'fee_p90',color:'#58a6ff33'},{low:'fee_p25',high:'fee_p75',color:'#37d67a55'}]});
      drawChart(el('blockFullnessChart'),points,[{key:'fullness_percent',color:'#d2a8ff',markers:true}],data?.bucket_seconds||300,{minimum:0,maximum:100});
    }
  }
  async function load(){
    const token=++generation;
    try{
      const response=await fetch(`/api/protocol-history?range=${encodeURIComponent(historyRange)}`,{cache:'no-store'});
      if(!response.ok)throw Error();
      const result=await response.json();if(token!==generation)return;data=result;
    }catch{if(token!==generation)return;data=null;}
    render();
  }
  for(const event of ['dashboard-view','resize','language-ready'])window.addEventListener(event,()=>requestAnimationFrame(render));
  window.addEventListener('history-range',()=>{data=null;render();load();});
  el('messageTrafficDetails').addEventListener('toggle',render);
  el('blockVisualDetails').addEventListener('toggle',render);
  render();load();setInterval(()=>{if(!document.hidden)load();},60000);
})();
