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
  'head','face','neck','back','chest_armor','chest_clothing','hands',
  'waist','legs_armor','legs_clothing','feet','ring_left','ring_right',
  'weapon_main','weapon_off','accessory_1','accessory_2'
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
  const labels = {
    head: 'HEAD', face: 'FACE', neck: 'NECK', back: 'BACK',
    chest_armor: 'CHEST \u00b7 ARMOR', chest_clothing: 'CHEST \u00b7 CLOTH',
    hands: 'HANDS', waist: 'WAIST',
    legs_armor: 'LEGS \u00b7 ARMOR', legs_clothing: 'LEGS \u00b7 CLOTH',
    feet: 'FEET',
    ring_left: 'RING \u00b7 L', ring_right: 'RING \u00b7 R',
    weapon_main: 'WEAPON \u00b7 MAIN', weapon_off: 'WEAPON \u00b7 OFF',
    accessory_1: 'ACC \u00b7 1', accessory_2: 'ACC \u00b7 2'
  };
  return labels[slot] || slot.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
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

  // Slot definitions: [x, y, width, height] for each slot rectangle on the body
  const slotDefs = {
    head:           { x: 88,  y: 12,  w: 28, h: 20 },
    face:           { x: 91,  y: 34,  w: 22, h: 14 },
    neck:           { x: 95,  y: 50,  w: 14, h: 12 },
    back:           { x: 80,  y: 72,  w: 44, h: 36 },
    chest_armor:    { x: 78,  y: 66,  w: 24, h: 32 },
    chest_clothing: { x: 102, y: 66,  w: 24, h: 32 },
    hands:          { x: 16,  y: 140, w: 24, h: 20 },
    waist:          { x: 85,  y: 104, w: 34, h: 16 },
    legs_armor:     { x: 81,  y: 124, w: 20, h: 44 },
    legs_clothing:  { x: 103, y: 124, w: 20, h: 44 },
    feet:           { x: 72,  y: 310, w: 28, h: 22 },
    ring_left:      { x: 14,  y: 116, w: 24, h: 16 },
    ring_right:     { x: 164, y: 116, w: 24, h: 16 },
    weapon_main:    { x: 4,   y: 140, w: 28, h: 36 },
    weapon_off:     { x: 170, y: 140, w: 28, h: 36 },
    accessory_1:    { x: 72,  y: 104, w: 18, h: 16 },
    accessory_2:    { x: 114, y: 104, w: 18, h: 16 }
  };

  // Label offsets (relative to slot center, dx/dy)
  const labelPos = {
    head:           { dx: 0,  dy: -8, anchor: 'middle' },
    face:           { dx: 0,  dy: -8, anchor: 'middle' },
    neck:           { dx: 0,  dy: -8, anchor: 'middle' },
    back:           { dx: 0,  dy: -8, anchor: 'middle' },
    chest_armor:    { dx: -28, dy: 0, anchor: 'end' },
    chest_clothing: { dx: 28,  dy: 0, anchor: 'start' },
    hands:          { dx: 0,  dy: 24, anchor: 'middle' },
    waist:          { dx: 0,  dy: 20, anchor: 'middle' },
    legs_armor:     { dx: -24, dy: 0, anchor: 'end' },
    legs_clothing:  { dx: 24,  dy: 0, anchor: 'start' },
    feet:           { dx: 0,  dy: 28, anchor: 'middle' },
    ring_left:      { dx: -24, dy: 0, anchor: 'end' },
    ring_right:     { dx: 24,  dy: 0, anchor: 'start' },
    weapon_main:    { dx: 0,  dy: -8, anchor: 'middle' },
    weapon_off:     { dx: 0,  dy: -8, anchor: 'middle' },
    accessory_1:    { dx: -22, dy: 0, anchor: 'end' },
    accessory_2:    { dx: 22,  dy: 0, anchor: 'start' }
  };

  let html = `<div style="margin-bottom:12px;"><div style="color:#8a7535;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Equipment</div>`;
  html += `<svg viewBox="0 0 200 360" style="display:block;margin:0 auto 10px;width:100%;max-width:200px;height:auto;">`;

  // Drop-shadow filter for filled slots
  html += `<defs><filter id="gold-glow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="0" stdDeviation="2" flood-color="#c8a84e" flood-opacity="0.5"/></filter></defs>`;

  // Body silhouette
  html += `<g fill="none" stroke="#3a3a4a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">`;
  // Head
  html += `<ellipse cx="100" cy="26" rx="18" ry="22"/>`;
  // Neck
  html += `<line x1="93" y1="48" x2="93" y2="56"/>`;
  html += `<line x1="107" y1="48" x2="107" y2="56"/>`;
  // Shoulders & torso
  html += `<path d="M68,56 L93,56 L93,62 L68,62 Z"/>`;
  html += `<path d="M107,56 L132,56 L132,62 L107,62 Z"/>`;
  html += `<path d="M68,62 Q64,66 62,72 L62,108 Q62,110 64,110 L136,110 Q138,110 138,108 L138,72 Q136,66 132,62"/>`;
  // Left arm: shoulder → elbow → hand
  html += `<path d="M62,72 L40,86 L28,130"/>`;
  html += `<line x1="28" y1="130" x2="20" y2="156"/>`;
  // Right arm
  html += `<path d="M138,72 L160,86 L172,130"/>`;
  html += `<line x1="172" y1="130" x2="180" y2="156"/>`;
  // Waist
  html += `<line x1="76" y1="110" x2="76" y2="120"/>`;
  html += `<line x1="124" y1="110" x2="124" y2="120"/>`;
  // Left leg
  html += `<path d="M76,120 L70,180 L68,280 L72,310"/>`;
  html += `<line x1="72" y1="310" x2="60" y2="330"/>`;
  // Right leg
  html += `<path d="M124,120 L130,180 L132,280 L128,310"/>`;
  html += `<line x1="128" y1="310" x2="140" y2="330"/>`;
  // Feet
  html += `<rect x="54" y="326" width="30" height="10" rx="3"/>`;
  html += `<rect x="116" y="326" width="30" height="10" rx="3"/>`;
  // Hands (small circles)
  html += `<circle cx="18" cy="160" r="5"/>`;
  html += `<circle cx="182" cy="160" r="5"/>`;
  html += `</g>`;

  // Back slot (dashed, rendered behind body)
  (() => {
    const d = slotDefs.back;
    const cx = d.x + d.w / 2;
    const cy = d.y + d.h / 2;
    const filled = equip['back'];
    const borderColor = filled ? '#c8a84e' : '#3a3a4a';
    const fillAttr = filled ? 'rgba(200,168,78,0.15)' : 'transparent';
    const filter = filled ? 'filter="url(#gold-glow)"' : '';
    const title = filled ? `<title>${esc(typeof filled === 'string' ? filled : (filled.name || 'back'))}</title>` : '';
    const abbrev = filled ? esc((typeof filled === 'string' ? filled : (filled.name || '')).substring(0, 3).toUpperCase()) : '';
    html += `<g class="equip-slot" data-slot="back" style="cursor:${filled ? 'pointer' : 'default'};">`;
    html += `<rect x="${d.x}" y="${d.y}" width="${d.w}" height="${d.h}" rx="3" fill="${fillAttr}" stroke="${borderColor}" stroke-width="1.5" stroke-dasharray="4 2" ${filter}/>`;
    if (abbrev) html += `<text x="${cx}" y="${cy + 3}" text-anchor="middle" font-size="7" fill="#c8a84e">${abbrev}</text>`;
    const lp = labelPos['back'];
    html += `<text x="${cx + lp.dx}" y="${cy + lp.dy}" text-anchor="${lp.anchor}" font-size="8" fill="${filled ? '#c8a84e' : '#4a4a5a'}">${getSlotLabel('back')}</text>`;
    html += title;
    html += `</g>`;
  })();

  // Render all equipment slots (except back, already rendered)
  EQUIP_SLOTS.forEach(slot => {
    if (slot === 'back') return;
    const d = slotDefs[slot];
    if (!d) return;
    const cx = d.x + d.w / 2;
    const cy = d.y + d.h / 2;
    const filled = equip[slot];
    const borderColor = filled ? '#c8a84e' : '#2a2a3a';
    const fillAttr = filled ? 'rgba(200,168,78,0.2)' : '#1a1a24';
    const filter = filled ? 'filter="url(#gold-glow)"' : '';
    const borderStyle = filled ? '' : 'stroke-dasharray="3 2"';
    const title = filled ? `<title>${esc(typeof filled === 'string' ? filled : (filled.name || slot))}</title>` : '';
    const abbrev = filled ? esc((typeof filled === 'string' ? filled : (filled.name || '')).substring(0, 3).toUpperCase()) : '';

    html += `<g class="equip-slot" data-slot="${slot}" style="cursor:${filled ? 'pointer' : 'default'};">`;
    html += `<rect x="${d.x}" y="${d.y}" width="${d.w}" height="${d.h}" rx="3" fill="${fillAttr}" stroke="${borderColor}" stroke-width="1.5" ${borderStyle} ${filter}/>`;
    if (abbrev) html += `<text x="${cx}" y="${cy + 3}" text-anchor="middle" font-size="7" fill="#c8a84e" font-weight="bold">${abbrev}</text>`;
    const lp = labelPos[slot];
    html += `<text x="${cx + lp.dx}" y="${cy + lp.dy}" text-anchor="${lp.anchor}" font-size="8" fill="${filled ? '#c8a84e' : '#6a6a7a'}">${getSlotLabel(slot)}</text>`;
    html += title;
    html += `</g>`;
  });

  html += `</svg>`;

  // Equipment list below the map
  html += `<div style="font-size:11px;">`;
  EQUIP_SLOTS.forEach(slot => {
    const item = equip[slot];
    if (item) {
      const name = typeof item === 'string' ? item : (item.name || slot);
      const rarity = (typeof item === 'object' ? item.rarity : '') || 'common';
      html += `<div class="equip-entry" data-slot="${slot}" style="display:flex;align-items:center;gap:6px;padding:2px 0;cursor:pointer;">
        <span style="color:#6a6a7a;font-size:10px;width:90px;">${getSlotLabel(slot)}</span>
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
