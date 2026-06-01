// save_manager.js — Save Manager Modal
// Canon Engine UI Module

import { showToast } from './toast.js';

let _modal = null;
let _saves = [];

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function getApiBase() {
  return (typeof window !== 'undefined' && window.API) || window.location.origin;
}

function getHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (typeof window !== 'undefined' && window.TOKEN) {
    h['Authorization'] = 'Bearer ' + window.TOKEN;
  }
  return h;
}

function createModal() {
  if (_modal) return _modal;
  const modal = document.createElement('div');
  modal.id = 'save-manager-ext';
  modal.className = 'modal';
  modal.style.zIndex = '115';
  modal.innerHTML = `
    <div class="modal-box" style="width:600px;max-height:80dvh;">
      <button class="close-btn" id="save-close">&times;</button>
      <h2>💾 SAVED GAMES</h2>
      <div id="save-list" style="overflow-y:auto;max-height:65dvh;"></div>
    </div>
  `;
  document.body.appendChild(modal);

  modal.querySelector('#save-close').addEventListener('click', closeSaves);
  modal.addEventListener('mousedown', (e) => {
    if (e.target === modal) closeSaves();
  });

  _modal = modal;
  return modal;
}

function renderSaveCard(save) {
  const hpPct = save.max_hp > 0 ? Math.round(save.hp / save.max_hp * 100) : 0;
  const date = save.modified ? new Date(save.modified * 1000) : null;
  const dateStr = date ? date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  let html = `<div class="save-card" data-slot="${esc(save.slot)}">`;
  html += `<div style="flex:1;">`;
  html += `<div class="save-name">${esc(save.character_name || save.name || 'Unknown')}</div>`;
  html += `<div class="save-meta">${esc(save.race || '')} ${esc(save.class_name || save.class || '')} — Level ${save.level || 1}</div>`;
  html += `<div class="save-meta">${esc((save.genre || '').replace(/_/g, ' '))} — ${esc(save.location || 'Unknown')}</div>`;

  // HP bar
  html += `<div style="display:flex;align-items:center;gap:6px;margin-top:4px;">`;
  html += `<span style="color:#555;font-size:11px;">HP</span>`;
  html += `<div style="flex:1;height:8px;background:var(--bg,#0a0a0a);border:1px solid rgba(58,58,92,0.3);overflow:hidden;">`;
  html += `<div style="height:100%;width:${hpPct}%;background:#cc3333;transition:width 0.3s;"></div>`;
  html += `</div>`;
  html += `<span style="color:#888;font-size:11px;">${save.hp || 0}/${save.max_hp || 0}</span>`;
  html += `</div>`;

  if (dateStr) {
    html += `<div class="save-slot-name" style="margin-top:4px;">Slot: ${esc(save.slot)} · ${dateStr}</div>`;
  }
  html += `</div>`;

  // Actions
  html += `<div class="save-actions">`;
  html += `<button class="btn-sm btn-load" data-action="load" data-slot="${esc(save.slot)}">LOAD</button>`;
  html += `<button class="btn-sm" data-action="copy" data-slot="${esc(save.slot)}">COPY</button>`;
  html += `<button class="btn-sm" data-action="rename" data-slot="${esc(save.slot)}">RENAME</button>`;
  html += `<button class="btn-sm btn-danger" data-action="delete" data-slot="${esc(save.slot)}">DELETE</button>`;
  html += `</div>`;

  html += `</div>`;
  return html;
}

function bindActions() {
  _modal.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      const slot = btn.dataset.slot;
      switch (action) {
        case 'load': loadSave(slot); break;
        case 'copy': copySave(slot); break;
        case 'rename': renameSave(slot); break;
        case 'delete': deleteSave(slot); break;
      }
    });
  });
}

async function refreshSaves() {
  const list = _modal.querySelector('#save-list');
  if (!list) return;
  list.innerHTML = '<div style="text-align:center;color:#666;padding:20px;">Loading saves...</div>';

  try {
    const resp = await fetch(getApiBase() + '/saves', { headers: getHeaders() });
    const data = await resp.json();
    _saves = data.saves || [];

    if (!_saves.length) {
      list.innerHTML = '<div style="text-align:center;color:#555;padding:40px;font-style:italic;">No saved games found.</div>';
      return;
    }

    list.innerHTML = _saves.map(s => renderSaveCard(s)).join('');
    bindActions();
  } catch (e) {
    list.innerHTML = '<div style="text-align:center;color:#cc3333;padding:20px;">Failed to load saves: ' + esc(e.message) + '</div>';
  }
}

export function openSaves() {
  createModal();
  _modal.classList.add('show');
  refreshSaves();
}

export function closeSaves() {
  if (_modal) _modal.classList.remove('show');
}

export async function loadSave(slot) {
  if (typeof window !== 'undefined') {
    window.SLOT = slot;
    closeSaves();
    if (typeof window.showScreen === 'function') window.showScreen('game');
    if (typeof window.cmd === 'function') window.cmd('/help');
    if (typeof showToast === 'function') showToast(`💾 Loaded: ${slot}`, { color: '#c8b16c' });
  }
}

export async function copySave(slot) {
  const name = prompt('Name for the copy:', slot + ' (copy)');
  if (!name) return;

  try {
    await fetch(getApiBase() + '/saves/duplicate', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ slot, target: name })
    });
    if (typeof showToast === 'function') showToast(`📋 Copied to: ${name}`, { color: '#33aa33' });
    refreshSaves();
  } catch (e) {
    if (typeof showToast === 'function') showToast(`❌ Copy failed: ${e.message}`, { color: '#cc3333' });
  }
}

export async function renameSave(slot) {
  const name = prompt('New name:', slot);
  if (!name) return;

  try {
    await fetch(getApiBase() + '/saves/rename', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ slot, target: name })
    });
    if (typeof showToast === 'function') showToast(`✏ Renamed to: ${name}`, { color: '#c8b16c' });
    refreshSaves();
  } catch (e) {
    if (typeof showToast === 'function') showToast(`❌ Rename failed: ${e.message}`, { color: '#cc3333' });
  }
}

export async function deleteSave(slot) {
  if (!confirm(`Delete save "${slot}"? This cannot be undone.`)) return;

  try {
    await fetch(getApiBase() + '/saves/delete', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ slot })
    });
    if (typeof showToast === 'function') showToast(`🗑 Deleted: ${slot}`, { color: '#cc3333' });
    refreshSaves();
  } catch (e) {
    if (typeof showToast === 'function') showToast(`❌ Delete failed: ${e.message}`, { color: '#cc3333' });
  }
}

export default { openSaves, closeSaves, loadSave, copySave, renameSave, deleteSave };
