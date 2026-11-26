// Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
// SPDX-License-Identifier: GPL-3.0-only
(() => {
  'use strict';
  const selected = new URL(location.href).searchParams.get('node') || 'local';
  const local = selected === 'local';
  const originalFetch = window.fetch.bind(window);
  const valid = /^[a-z][a-z0-9-]{0,31}$/.test(selected);
  const prefix = `/api/nodes/${valid ? selected : 'invalid'}/`;
  function nodeURL(value) {
    if (typeof value === 'string' && value.startsWith('/api/') &&
        !value.startsWith('/api/admin/') && !value.startsWith('/api/nodes')) {
      return local ? value : prefix + value.slice(5);
    }
    return value;
  }
  window.fetch = (input, options) => originalFetch(nodeURL(input), options);
  if (window.EventSource) {
    const OriginalEventSource = window.EventSource;
    window.EventSource = class extends OriginalEventSource {
      constructor(url, options) { super(nodeURL(url), options); }
    };
  }
  document.addEventListener('DOMContentLoaded', async () => {
    const label = document.getElementById('nodePicker');
    const select = document.getElementById('nodeSelect');
    const admin = document.getElementById('adminLink');
    if (!local) {
      admin.hidden = true;
      label.hidden = false;
      select.append(new Option(selected, selected, true, true));
    }
    try {
      const response = await originalFetch('/api/nodes', {cache: 'no-store'});
      if (!response.ok) throw new Error('Node list unavailable');
      const data = await response.json();
      if (!Array.isArray(data.nodes) || !data.nodes.length) throw new Error('Empty node list');
      select.replaceChildren();
      for (const node of data.nodes) select.append(new Option(node.name, node.id));
      if (!data.nodes.some(node => node.id === selected)) {
        select.append(new Option(selected, selected));
      }
      select.value = selected;
      label.hidden = local && data.nodes.length === 1;
      document.title = `${select.selectedOptions[0].textContent} · Bitcoin Node`;
    } catch {
      if (!local) select.value = selected;
    }
    select.addEventListener('change', () => {
      const target = new URL(location.href);
      if (select.value === 'local') target.searchParams.delete('node');
      else target.searchParams.set('node', select.value);
      location.assign(target.href);
    });
  });
})();
