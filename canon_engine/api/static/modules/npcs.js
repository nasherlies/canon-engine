// npcs.js — NPC Interaction Panel
// Canon Engine UI Module

import { show as showToast } from './toast.js';
import { get as getState, set as setState } from './store.js';

let _overlay = null;
let _layout = null;
let _giftPickerNPC = null;

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function relBarColor(value) {
  // -100 to 100 scale, map to colors
  if (value <= -60) return '#cc3333';
  if (value <= -20) return '#cc6633';
  if (value <= 20) return '#666666';
  if (value <= 60) return '#33aa33';
  return '#c8b16c';
}

function relLabel(value) {
  if (value <= -60) return 'Hostile';
  if (value <= -20) return 'Unfriendly';
  if (value <= 20) return 'Neutral';
  if (value <= 60) return 'Friendly';
  return 'Allied';
}

function createOverlay() {
  if (_overlay) return _overlay;
  const overlay = document.createElement('div');
  overlay.id = 'npcs-overlay';
  overlay.className = 'modal';
  overlay.style.zIndex = '105';
  overlay.innerHTML = `
    <div class="modal-box" style="width:520px;max-height:85dvh;">
      <button class="close-btn" id="npcs-close">&times;</button>
      <h2>🤝 NPC INTERACTIONS</h2>
      <div id="npcs-body" style="overflow-y:auto;max-height:70dvh;"></div>
    </div>
    <div id="gift-picker" class="modal" style="z-index:110;display:none;">
      <div class="modal-box" style="width:340px;">
        <button class="close-btn" id="gift-close">&times;</button>
        <h2>🎁 SELECT GIFT</h2>
        <div id="gift-items" style="max-height:50dvh;overflow-y:auto;"></div>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector('#npcs-close').addEventListener('click', closeNPCs);
  overlay.addEventListener('mousedown', (e) => {
    if (e.target === overlay) closeNPCs();
  });
  overlay.querySelector('#gift-close').addEventListener('click', () => {
    const gp = overlay.querySelector('#gift-picker');
    if (gp) gp.style.display = 'none';
    _giftPickerNPC = null;
  });

  _overlay = overlay;
  return overlay;
}

function renderNPCCard(npc, index) {
  const rel = npc.relationship !== undefined ? npc.relationship : npc.rep || 0;
  const relPct = Math.round((rel + 100) / 2); // map -100..100 to 0..100
  const relColor = relBarColor(rel);
  const recruitable = npc.recruitable || npc.can_recruit;

  let html = `<div class="npc-card" style="
    background:rgba(26,26,46,0.7);border:1px solid rgba(58,58,92,0.3);
    padding:12px;margin-bottom:10px;
  ">`;

  // Header row
  html += `<div style="display:flex;justify-content:space-between;align-items:center;">`;
  html += `<div>`;
  html += `<div style="color:#c8b16c;font-size:15px;font-weight:bold;">${esc(npc.name || 'Unknown')}</div>`;
  html += `<div style="color:#888;font-size:12px;">${esc(npc.role || npc.class || '')}</div>`;
  html += `</div>`;
  if (npc.faction) {
    html += `<div style="color:#666;font-size:11px;border:1px solid rgba(58,58,92,0.3);padding:2px 8px;">${esc(npc.faction)}</div>`;
  }
  html += `</div>`;

  // Relationship bar
  html += `<div style="margin-top:8px;">`;
  html += `<div style="display:flex;justify-content:space-between;font-size:11px;color:#555;">`;
  html += `<span>Hostile</span><span>${relLabel(rel)}</span><span>Friendly</span>`;
  html += `</div>`;
  html += `<div style="height:8px;background:var(--bg,#0a0a0a);border:1px solid rgba(58,58,92,0.3);margin-top:2px;overflow:hidden;">`;
  html += `<div style="height:100%;width:${Math.max(0, Math.min(100, relPct))}%;background:${relColor};transition:width 0.4s;"></div>`;
  html += `</div>`;
  html += `</div>`;

  // Recent memory events
  if (npc.memory && npc.memory.length > 0) {
    html += `<div style="margin-top:8px;">`;
    html += `<div style="color:#555;font-size:10px;letter-spacing:1px;margin-bottom:4px;">RECENT INTERACTIONS</div>`;
    npc.memory.slice(-3).forEach(m => {
      html += `<div style="color:#666;font-size:11px;padding:2px 0;border-bottom:1px solid rgba(58,58,92,0.15);">`;
      html += `• ${esc(typeof m === 'string' ? m : m.text || m.description || '')}`;
      html += `</div>`;
    });
    html += `</div>`;
  }

  // Action buttons
  html += `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;">`;
  html += `<button class="btn" style="flex:1;min-height:36px;font-size:12px;" data-action="talk" data-idx="${index}">💬 TALK</button>`;
  html += `<button class="btn" style="flex:1;min-height:36px;font-size:12px;" data-action="gift" data-idx="${index}">🎁 GIFT</button>`;
  html += `<button class="btn" style="flex:1;min-height:36px;font-size:12px;border-color:#cc3333;color:#cc3333;" data-action="threaten" data-idx="${index}">⚔ THREATEN</button>`;
  if (recruitable) {
    html += `<button class="btn" style="flex:1;min-height:36px;font-size:12px;border-color:#33aa33;color:#33aa33;" data-action="recruit" data-idx="${index}">⚑ RECRUIT</button>`;
  }
  html += `</div>`;

  html += `</div>`;
  return html;
}

function renderGiftPicker(npcId, inventory) {
  const picker = _overlay.querySelector('#gift-items');
  if (!picker) return;

  if (!inventory || !inventory.length) {
    picker.innerHTML = '<div style="text-align:center;color:#555;padding:20px;">No items to gift.</div>';
    return;
  }

  picker.innerHTML = inventory.map((item, i) => {
    const name = typeof item === 'string' ? item : (item.name || 'Unknown');
    return `<div class="inv-item" style="cursor:pointer;padding:8px;border-bottom:1px solid rgba(58,58,92,0.2);" data-gift-item="${esc(name)}" data-gift-npc="${npcId}">
      <span style="color:#a3a3a3;font-size:13px;">${esc(name)}</span>
    </div>`;
  }).join('');

  picker.querySelectorAll('[data-gift-item]').forEach(el => {
    el.addEventListener('click', () => {
      const item = el.dataset.giftItem;
      const npc = el.dataset.giftNpc;
      giftNPCWithItem(npc, item);
    });
  });
}

function giftNPCWithItem(npcId, itemName) {
  const picker = _overlay.querySelector('#gift-picker');
  if (picker) picker.style.display = 'none';
  _giftPickerNPC = null;

  if (typeof window.cmd === 'function') {
    window.cmd(`/gift ${itemName} to ${npcId}`);
  }
  if (typeof showToast === 'function') {
    showToast(`🎁 Gifting ${itemName}...`, { color: '#c8b16c' });
  }
}

function renderLayout(layout) {
  _layout = layout || {};
  const body = _overlay.querySelector('#npcs-body');
  if (!body) return;

  const npcs = layout.npcs || layout.npc || [];
  if (!npcs.length) {
    body.innerHTML = '<div style="text-align:center;color:#555;padding:40px;font-style:italic;">No NPCs at this location.</div>';
    return;
  }

  body.innerHTML = npcs.map((npc, i) => renderNPCCard(npc, i)).join('');

  // Button handlers
  body.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      const idx = parseInt(btn.dataset.idx);
      const npc = npcs[idx];
      if (!npc) return;

      const npcId = npc.id || npc.name || '';
      switch (action) {
        case 'talk': talkToNPC(npcId); break;
        case 'gift': giftNPC(npcId); break;
        case 'threaten': threatenNPC(npcId); break;
        case 'recruit': recruitNPC(npcId); break;
      }
    });
  });
}

export function openNPCs(layout) {
  _layout = layout || {};
  createOverlay();
  renderLayout(_layout);
  _overlay.classList.add('show');
}

export function closeNPCs() {
  if (_overlay) _overlay.classList.remove('show');
}

export function talkToNPC(id) {
  if (typeof window.cmd === 'function') {
    window.cmd(`/talk ${id}`);
  }
  if (typeof showToast === 'function') {
    showToast(`💬 Talking to ${id}...`, { color: '#6cb4c8' });
  }
}

export function giftNPC(id) {
  _giftPickerNPC = id;
  const inventory = (typeof getState === 'function' ? getState('inventory') : null) || window.PLAYER?.inventory || [];
  createOverlay();
  const picker = _overlay.querySelector('#gift-picker');
  if (picker) {
    picker.style.display = 'flex';
    renderGiftPicker(id, inventory);
  }
}

export function threatenNPC(id) {
  if (typeof window.cmd === 'function') {
    window.cmd(`/threaten ${id}`);
  }
  if (typeof showToast === 'function') {
    showToast(`⚔ Threatening ${id}...`, { color: '#cc3333' });
  }
}

export function recruitNPC(id) {
  if (typeof window.cmd === 'function') {
    window.cmd(`/recruit ${id}`);
  }
  if (typeof showToast === 'function') {
    showToast(`⚑ Recruiting ${id}...`, { color: '#33aa33' });
  }
}

export default { openNPCs, closeNPCs, talkToNPC, giftNPC, threatenNPC, recruitNPC };
