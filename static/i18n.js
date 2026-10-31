// Copyright (C) 2026 Hardy (todo1971)
// SPDX-License-Identifier: GPL-3.0-only
/* Local catalogs only. Never translate logs, credentials or form values. */
(() => {
  'use strict';
  let language = 'de';
  try { if (localStorage.getItem('dashboard-language') === 'en') language = 'en'; } catch {}
  const locale = language === 'en' ? 'en-GB' : 'de-DE';
  let catalog = {}, pattern;
  const escape = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  function text(value) {
    if (language === 'de' || !pattern) return value;
    if (Object.hasOwn(catalog, value)) return catalog[value];
    return value.replace(pattern, match => catalog[match]);
  }
  window.I18n = {language, locale, text};
  document.documentElement.lang = language;
  const skip = 'script,style,pre,code,textarea,select,[data-no-i18n]';
  function translate(root) {
    if (root.nodeType === Node.TEXT_NODE) {
      if (!root.parentElement?.closest(skip)) {
        const result = text(root.nodeValue);
        if (result !== root.nodeValue) root.nodeValue = result;
      }
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE || root.closest(skip)) return;
    for (const name of ['title', 'aria-label', 'placeholder']) {
      if (root.hasAttribute(name)) {
        const original = root.getAttribute(name), result = text(original);
        if (result !== original) root.setAttribute(name, result);
      }
    }
    for (const child of root.childNodes) translate(child);
  }
  document.addEventListener('DOMContentLoaded', async () => {
    const label = document.createElement('label');
    label.style.cssText = 'display:inline-flex;gap:8px;align-items:center;margin:12px 0';
    label.textContent = language === 'en' ? 'Language' : 'Sprache';
    const select = document.createElement('select');
    select.setAttribute('aria-label', 'Language / Sprache');
    select.style.cssText = 'background:#151a20;color:#eef2f6;border:1px solid #29313a;border-radius:6px;padding:6px';
    for (const [value, title] of [['de', 'Deutsch'], ['en', 'English']]) {
      const option = document.createElement('option');
      option.value = value; option.textContent = title; select.append(option);
    }
    select.value = language;
    select.addEventListener('change', () => {
      try { localStorage.setItem('dashboard-language', select.value); location.reload(); }
      catch { select.value = language; }
    });
    label.append(select);
    document.querySelector('header').after(label);
    if (language === 'de') return;
    try {
      const response = await fetch(`/static/locales/${language}.json`, {cache:'no-cache'});
      if (!response.ok) throw Error(response.status);
      catalog = await response.json();
      // Longest phrase first; Unicode boundaries protect identifiers and addresses.
      const keys = Object.keys(catalog).filter(key => key !== catalog[key]).sort((a,b) => b.length-a.length);
      pattern = new RegExp(`(?<![\\p{L}\\p{N}_])(?:${keys.map(escape).join('|')})(?![\\p{L}\\p{N}_])`, 'gu');
      translate(document.documentElement);
      const observer = new MutationObserver(records => {
        for (const record of records) {
          if (record.type === 'childList') for (const node of record.addedNodes) translate(node);
          else translate(record.target);
        }
      });
      observer.observe(document.body, {subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['title','aria-label','placeholder']});
      window.dispatchEvent(new Event('language-ready'));
    } catch (error) {
      document.documentElement.lang = 'de';
      const notice = document.createElement('p');
      notice.textContent = 'English could not be loaded. Deutsche Oberfläche wird angezeigt.';
      label.after(notice);
      console.error('Language catalog unavailable', error);
    }
  });
})();
