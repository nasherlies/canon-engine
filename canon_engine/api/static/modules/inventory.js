// ─── inventory.js ─── Inventory Panel ───
import { action } from './api.js';
import * as store from './store.js';
import { show as toast } from './toast.js';

/* ── Constants ── */
const RARITY_ORDER = { mythical: 0, legendary: 1, epic: 2, rare: 3, uncommon: 4, common: 5 };
const RARITY_COLORS = {
  common: '#888', uncommon: '#4CAF50', rare: '#2196F3',
  epic: '#9C27B0', legendary: '#FFD700', mythical: '#f44336'
};

const EQUIP_SLOTS = [
  'head','face','neck','shoulders','chest','back','wrists','hands',
  'waist','legs','feet','finger_1','finger_2','main_hand','off_hand','ranged','artifact'
];

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function rarityColor(r) {
  return RARITY_COLORS[(r || '').toLowerCase()] || '#888';
}

function sortItems(items) {
  return [...items].sort((a, b) => {
    const ra = RARITY_ORDER[(a.rarity || '').toLowerCase()] ?? 6;
    const rb = RARITY_ORDER[(b.rarity || '').toLowerCase()] ?? 6;
    return ra - rb;
  });
}

function getSlotLabel(slot) {
  return slot.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

let _expandedItem = null;
let _confirmDrop = null;

/* ── Render item row ── */
function renderItemRow(item, index) {
  const name = item.name || 'Item';
  const qty = item.quantity || item.qty || 1;
  const weight = item.weight || 0;
  const rarity = (item.rarity || 'common').toLowerCase();
  const isConsumable = item.type === 'consumable' || item.category === 'consumable';
  const isGear = item.type === 'gear' || item.type === 'equipment' || item.equippable;
  const expanded = _expandedItem === index;

  let html = `<div class="inv-row" data-idx="${index}" style="border-bottom:1px solid #2a2a3a;padding:6px 8px;cursor:pointer;transition:background 0.15s;">
    <div style="display:flex;align-items:center;gap:8px;">
      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${rarityColor(rarity)};flex-shrink:0;"></span>
      <span style="color:${rarityColor(rarity)};flex:1;font-size:12px;">${esc(name)}</span>
      ${qty > 1 ? `<span style="color:#6a6a7a;font-size:11px;">×${qty}</span>` : ''}
      <span style="color:#6a6a7a;font-size:10px;">${weight}lb</span>
    </div>`;

  if (expanded) {
    html += `<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px;">`;
    if (isConsumable) html += `<button class="btn btn-small inv-use" data-name="${esc(name)}">USE</button>`;
    if (isGear) {
      html += `<button class="btn btn-small inv-equip" data-name="${esc(name)}">${item.equipped ? 'UNEQUIP' : 'EQUIP'}</button>`;
    }
    html += `<button class="btn btn-small inv-inspect" data-name="${esc(name)}">INSPECT</button>`;
    html += `<button class="btn btn-small inv-combine" data-name="${esc(name)}">COMBINE</button>`;
    if (_confirmDrop === index) {
      html += `<button class="btn btn-small inv-drop-confirm" data-name="${esc(name)}" style="border-color:#c44;color:#c44;">CONFIRM DROP</button>`;
    } else {
      const needsConfirm = ['rare','epic','legendary','mythical'].includes(rarity);
      html += `<button class="btn btn-small inv-drop" data-name="${esc(name)}" data-confirm="${needsConfirm}">DROP</button>`;
    }
    if (item.lore || item.description) {
      html += `</div><div style="margin-top:4px;padding:6px;background:#0a0a0f;border:1px solid #2a2a3a;font-size:11px;color:#6a6a7a;line-height:1.4;">${esc(item.lore || item.description)}</div>`;
    }
    html += `</div>`;
  }
  html += `</div>`;
  return html;
}

/* ── Equipment SVG silhouette ── */
function renderEquipmentMap(equipment) {
  const equip = equipment || {};
  let html = `<div style="margin-bottom:12px;"><div style="color:#8a7535;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Equipment</div>`;
  html += `<svg viewBox="0 0 120 200" width="120" height="200" style="display:block;margin:0 auto 10px;">`;
  html += `<g fill="none" stroke="#2a2a3a" stroke-width="1">`;
  html += `<circle cx="60" cy="20" r="12"/><line x1="60" y1="32" x2="60" y2="38"/>`;
  html += `<rect x="40" y="38" width="40" height="50" rx="3"/>`;
  html += `<line x1="40" y1="42" x2="22" y2="75"/><line x1="80" y1="42" x2="98" y2="75"/>`;
  html += `<line x1="50" y1="88" x2="42" y2="140"/><line x1="70" y1="88" x2="78" y2="140"/>`;
  html += `<line x1="42" y1="140" x2="34" y2="148"/><line x1="78" y1="140" x2="86" y2="148"/>`;
  html += `</g>`;

  const slotPos = {
    head:[60,12], face:[60,24], neck:[60,36], shoulders:[36,42],
    chest:[60,58], back:[60,48], wrists:[18,72], hands:[14,80],
    waist:[60,82], legs:[60,110], feet:[40,148],
    finger_1:[10,88], finger_2:[110,88], main_hand:[14,95], off_hand:[106,95],
    ranged:[110,60], artifact:[60,168]
  };

  EQUIP_SLOTS.forEach(slot => {
    const pos = slotPos[slot];
    if (!pos) return;
    const filled = equip[slot];
    const color = filled ? '#c8a84e' : '#2a2a3a';
    const fill = filled ? 'rgba(200,168,78,0.3)' : 'transparent';
    html += `<circle cx="${pos[0]}" cy="${pos[1]}" r="7" fill="${fill}" stroke="${color}" stroke-width="1.5" class="equip-slot" data-slot="${slot}" style="cursor:${filled ? 'pointer' : 'default'};"/>`;
    html += `<text x="${pos[0]}" y="${pos[1]+3}" text-anchor="middle" font-size="6" fill="${filled ? '#c8a84e' : '#6a6a7a'}">${slot.charAt(0).toUpperCase()}</text>`;
  });
  html += `</svg>`;

  html += `<div style="font-size:11px;">`;
  EQUIP_SLOTS.forEach(slot => {
    const item = equip[slot];
    if (item) {
      const name = typeof item === 'string' ? item : (item.name || slot);
      const rarity = (typeof item === 'object' ? item.rarity : '') || 'common';
      html += `<div class="equip-entry" data-slot="${slot}" style="display:flex;align-items:center;gap:6px;padding:2px 0;cursor:pointer;">
        <span style="color:#6a6a7a;font-size:10px;width:70px;">${getSlotLabel(slot)}</span>
        <span style="color:${rarityColor(rarity)};font-size:11px;">${esc(name)}</span>
      </div>`;
    }
  });
  html += `</div></div>`;
  return html;
}

/* ── Carry weight bar ── */
function renderCarryBar(carry, capacity) {
  const c = carry || 0;
  const cap = capacity || 100;
  const pct = Math.min(Math.round(c / cap * 100), 100);
  const over = c > cap;
  return `<div style="margin-bottom:10px;">
    <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">
      <span style="color:#6a6a7a;">Carry Weight</span>
      <span style="color:${over ? '#c44' : '#c8c8d0'};">${c} / ${cap}</span>
    </div>
    <div style="height:6px;background:#0a0a0f;border:1px solid #2a2a3a;border-radius:2px;">
      <div style="height:100%;width:${pct}%;background:${over ? '#c44' : '#c8a84e'};border-radius:1px;transition:width 0.5s;"></div>
    </div>
  </div>`;
}

function renderGold(gold) {
  return `<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;font-size:12px;">
    <span style="color:#c8a84e;">⬡</span>
    <span style="color:#c8a84e;font-weight:bold;">${gold ?? 0} Gold</span>
  </div>`;
}

/* ── Sidebar render ── */
export function renderInventorySidebar(items, equipment, carry, cap) {
  const body = document.getElementById('sp-inventory-body');
  if (!body) return;
  let html = renderGold(store.get('player')?.gold ?? 0);
  const sorted = sortItems(items || []);
  sorted.forEach(item => {
    const name = item.name || 'Item';
    const qty = item.quantity || item.qty || 1;
    const rarity = (item.rarity || 'common').toLowerCase();
    html += `<div style="padding:2px 0;font-size:12px;display:flex;align-items:center;gap:4px;">
      <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${rarityColor(rarity)};"></span>
      <span style="color:${rarityColor(rarity)};">${esc(name)}</span>
      ${qty > 1 ? `<span style="color:#6a6a7a;font-size:10px;">×${qty}</span>` : ''}
    </div>`;
  });
  if (sorted.length === 0) html += '<div style="color:#6a6a7a;font-size:11px;">Empty</div>';
  body.innerHTML = html;
}

/* ── Full overlay render ── */
export function renderInventoryOverlay(items, equipment, carry, cap) {
  let ov = document.getElementById('inventory-overlay');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'inventory-overlay';
    ov.style.cssText = `position:fixed;inset:0;z-index:800;display:none;background:rgba(0,0,0,0.90);overflow-y:auto;font-family:var(--mono,'Cascadia Mono','Fira Code',monospace);padding:20px;color:#c8c8d0;`;
    document.body.appendChild(ov);
  }

  const sorted = sortItems(items || []);
  let html = `<div style="max-width:800px;margin:0 auto;">`;
  html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
    <div style="color:#c8a84e;font-size:16px;letter-spacing:2px;">◆ INVENTORY</div>
    <button class="btn btn-small" id="inv-close-btn">CLOSE</button>
  </div>`;
  html += renderGold(store.get('player')?.gold ?? 0);
  html += renderCarryBar(carry, cap);
  html += renderEquipmentMap(equipment);

  html += `<div style="margin-bottom:10px;"><div style="color:#8a7535;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Items</div>`;
  sorted.forEach((item, i) => { html += renderItemRow(item, i); });
  if (sorted.length === 0) html += '<div style="color:#6a6a7a;font-size:11px;padding:8px;">No items</div>';
  html += `</div></div>`;

  ov.innerHTML = html;
  ov.style.display = 'flex';

  // Event bindings
  ov.querySelectorAll('.inv-row').forEach(row => {
    row.addEventListener('click', (e) => {
      if (e.target.tagName === 'BUTTON') return;
      const idx = parseInt(row.dataset.idx);
      _expandedItem = _expandedItem === idx ? null : idx;
      _confirmDrop = null;
      renderInventoryOverlay(items, equipment, carry, cap);
    });
  });
  ov.querySelectorAll('.inv-use').forEach(btn => btn.addEventListener('click', () => useItem(btn.dataset.name)));
  ov.querySelectorAll('.inv-equip').forEach(btn => btn.addEventListener('click', () => equipItem(btn.dataset.name)));
  ov.querySelectorAll('.inv-inspect').forEach(btn => btn.addEventListener('click', () => inspectItem(btn.dataset.name)));
  ov.querySelectorAll('.inv-combine').forEach(btn => btn.addEventListener('click', () => toast('Combine: select second item', 'info')));
  ov.querySelectorAll('.inv-drop').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.confirm === 'true') {
        _confirmDrop = parseInt(btn.closest('.inv-row').dataset.idx);
        renderInventoryOverlay(items, equipment, carry, cap);
      } else {
        dropItem(btn.dataset.name);
      }
    });
  });
  ov.querySelectorAll('.inv-drop-confirm').forEach(btn => btn.addEventListener('click', () => dropItem(btn.dataset.name)));
  ov.querySelectorAll('.equip-entry').forEach(entry => {
    entry.addEventListener('click', () => {
      const item = (equipment || {})[entry.dataset.slot];
      if (item) equipItem(typeof item === 'string' ? item : (item.name || ''));
    });
  });
  const closeBtn = document.getElementById('inv-close-btn');
  if (closeBtn) closeBtn.addEventListener('click', () => { ov.style.display = 'none'; });
}

/* ── Action handlers ── */
async function sendItemCmd(cmd, name) {
  const slot = store.get('slot') || 'default';
  try {
    const d = await action(`${cmd} ${name}`, { slot });
    store.emit('narration', d.narration);
    store.emit('layout', d.layout);
    store.emit('state', d.state);
    toast(`${cmd} ${name}`, 'info');
  } catch (e) {
    toast('Failed: ' + e.message, 'error');
  }
}

export function useItem(name) { sendItemCmd('/use', name); }
export function equipItem(name) { sendItemCmd('/equip', name); }
export function dropItem(name) { sendItemCmd('/drop', name); _confirmDrop = null; }
export function inspectItem(name) { sendItemCmd('/inspect', name); }
