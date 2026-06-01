// codex.js — Lore Codex Overlay
// Canon Engine UI Module

import { show as showToast } from './toast.js';
import { get as getState, set as setState } from './store.js';

const CATEGORY_COLORS = {
  CHARACTER: { bg: '#c8b16c', color: '#000' },
  CHARACTERS: { bg: '#c8b16c', color: '#000' },
  LOCATION: { bg: '#6cb4c8', color: '#000' },
  LOCATIONS: { bg: '#6cb4c8', color: '#000' },
  FACTION: { bg: '#c86c6c', color: '#000' },
  FACTIONS: { bg: '#c86c6c', color: '#000' },
  ITEM: { bg: '#6cc86c', color: '#000' },
  ITEMS: { bg: '#6cc86c', color: '#000' },
  HISTORY: { bg: '#b46cc8', color: '#000' },
  LORE: { bg: '#b46cc8', color: '#000' },
  BESTIARY: { bg: '#c89b6c', color: '#000' }
};

const TABS = ['ALL', 'CHARACTERS', 'LOCATIONS', 'FACTIONS', 'ITEMS', 'HISTORY'];

let _overlay = null;
let _currentTab = 'ALL';
let _layout = null;

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function createOverlay() {
  if (_overlay) return _overlay;
  const overlay = document.createElement('div');
  overlay.id = 'codex-overlay';
  overlay.className = 'modal';
  overlay.style.zIndex = '105';
  overlay.innerHTML = `
    <div class="modal-box" style="width:600px;max-height:85dvh;">
      <button class="close-btn" id="codex-close">&times;</button>
      <h2>📖 LORE CODEX</h2>
      <div id="codex-discovery" style="text-align:center;color:#666;font-size:12px;margin-bottom:12px;"></div>
      <div class="set-tabs" id="codex-tabs"></div>
      <div id="codex-body" style="overflow-y:auto;max-height:62dvh;"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector('#codex-close').addEventListener('click', closeCodex);
  overlay.addEventListener('mousedown', (e) => {
    if (e.target === overlay) closeCodex();
  });

  _overlay = overlay;
  return overlay;
}

function renderTabs() {
  const tabsEl = _overlay.querySelector('#codex-tabs');
  if (!tabsEl) return;
  tabsEl.innerHTML = TABS.map(tab => {
    const active = tab === _currentTab ? ' active' : '';
    return `<button class="set-tab${active}" data-tab="${tab}">${tab}</button>`;
  }).join('');

  tabsEl.querySelectorAll('.set-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      _currentTab = btn.dataset.tab;
      renderTabs();
      renderEntries();
    });
  });
}

function getFilteredEntries(entries) {
  if (_currentTab === 'ALL') return entries;
  return entries.filter(e => {
    const cat = (e.category || e.type || '').toUpperCase();
    if (_currentTab === 'CHARACTERS') return cat === 'CHARACTER' || cat === 'CHARACTERS';
    if (_currentTab === 'LOCATIONS') return cat === 'LOCATION' || cat === 'LOCATIONS';
    if (_currentTab === 'FACTIONS') return cat === 'FACTION' || cat === 'FACTIONS';
    if (_currentTab === 'ITEMS') return cat === 'ITEM' || cat === 'ITEMS';
    if (_currentTab === 'HISTORY') return cat === 'HISTORY' || cat === 'LORE';
    return true;
  });
}

function renderEntries() {
  const body = _overlay.querySelector('#codex-body');
  if (!body) return;

  const allEntries = _layout.entries || _layout.codex || [];
  const entries = getFilteredEntries(allEntries);

  if (!entries.length) {
    body.innerHTML = '<div style="text-align:center;color:#555;padding:40px;font-style:italic;">No codex entries found. Explore to discover lore!</div>';
    return;
  }

  let html = '';
  entries.forEach(entry => {
    const locked = entry.locked || entry.hidden || !entry.discovered;
    const cat = (entry.category || entry.type || 'LORE').toUpperCase();
    const catStyle = CATEGORY_COLORS[cat] || CATEGORY_COLORS.LORE;

    html += `<div class="codex-card" style="
      background:rgba(26,26,46,0.7);border:1px solid rgba(58,58,92,0.3);
      padding:12px;margin-bottom:8px;position:relative;
      ${locked ? 'filter:blur(4px);user-select:none;' : ''}
    ">`;

    // Category badge
    html += `<span style="
      display:inline-block;background:${catStyle.bg};color:${catStyle.color};
      font-size:10px;font-weight:bold;padding:2px 8px;letter-spacing:1px;
      margin-bottom:6px;
    ">${esc(cat)}</span>`;

    // Title
    html += `<div style="color:#c8b16c;font-size:15px;font-family:Georgia,serif;margin-top:4px;">${esc(entry.title || entry.name || 'Unknown')}</div>`;

    // Description
    if (entry.description || entry.text) {
      html += `<div style="color:#888;font-size:13px;margin-top:6px;line-height:1.5;">${esc(entry.description || entry.text)}</div>`;
    }

    // Discovery info
    if (entry.discoveredAt || entry.location || entry.discovery_location) {
      html += `<div style="color:#555;font-size:11px;margin-top:6px;font-style:italic;">`;
      html += `Discovered: ${esc(entry.discoveredAt || entry.location || entry.discovery_location)}`;
      html += `</div>`;
    }

    html += `</div>`;

    // Locked overlay
    if (locked) {
      html += `<div style="
        position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
        color:#555;font-size:36px;font-weight:bold;z-index:2;
        text-shadow:0 0 10px rgba(0,0,0,0.8);
      ">?</div>`;
    }
  });

  body.innerHTML = html;

  // Update discovery ratio
  const total = allEntries.length;
  const discovered = allEntries.filter(e => e.discovered && !e.locked && !e.hidden).length;
  const discEl = _overlay.querySelector('#codex-discovery');
  if (discEl) {
    discEl.textContent = `Discovered: ${discovered} / ${total} (${total > 0 ? Math.round(discovered / total * 100) : 0}%)`;
  }
}

function renderLayout(layout) {
  _layout = layout || {};
  renderTabs();
  renderEntries();
}

export function openCodex(layout) {
  _layout = layout || {};
  _currentTab = 'ALL';
  createOverlay();
  renderLayout(_layout);
  _overlay.classList.add('show');
}

export function closeCodex() {
  if (_overlay) _overlay.classList.remove('show');
}

export function discoverCard(pulse) {
  if (!pulse) return;
  const entry = pulse.entry || pulse.card || pulse;
  const title = entry.title || entry.name || 'something';

  if (typeof showToast === 'function') {
    showToast(`📖 Discovered: ${title}`, { color: '#b46cc8', duration: 3000 });
  }

  if (typeof setState === 'function') {
    const codex = getState('codex') || [];
    const existing = codex.findIndex(e => e.id === entry.id || e.title === entry.title);
    if (existing >= 0) {
      codex[existing] = { ...codex[existing], ...entry, discovered: true, locked: false };
    } else {
      codex.push({ ...entry, discovered: true, locked: false });
    }
    setState('codex', codex);
  }
}

export default { openCodex, closeCodex, discoverCard };
