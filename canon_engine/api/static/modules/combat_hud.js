// ─── combat_hud.js ─── Combat Overlay ───
import { action } from './api.js';
import * as store from './store.js';
import { show as toast } from './toast.js';

let _layout = null;
let _selectedIndex = -1;

/* ── Helpers ── */
function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function hpPct(cur, max) {
  if (!max || max <= 0) return 0;
  return Math.min(Math.round(cur / max * 100), 100);
}

/* ── Duplicate enemy numbering ── */
function numberEnemies(enemies) {
  const counts = {};
  const nameCounts = {};
  // First pass: count duplicates
  enemies.forEach(e => {
    const base = e.name || 'Enemy';
    nameCounts[base] = (nameCounts[base] || 0) + 1;
  });
  // Second pass: assign display names
  return enemies.map(e => {
    const base = e.name || 'Enemy';
    counts[base] = (counts[base] || 0) + 1;
    return {
      ...e,
      displayName: nameCounts[base] > 1 ? base + ' ' + counts[base] : base
    };
  });
}

/* ── Build overlay DOM ── */
function ensureOverlay() {
  let ov = document.getElementById('combat-overlay');
  if (ov) return ov;
  ov = document.createElement('div');
  ov.id = 'combat-overlay';
  ov.style.cssText = `position:fixed;inset:0;z-index:900;display:none;background:rgba(0,0,0,0.92);overflow-y:auto;font-family:var(--mono,'Cascadia Mono','Fira Code',monospace);padding:20px;color:#c8c8d0;`;
  document.body.appendChild(ov);
  return ov;
}

/* ── Render ── */
function render(layout) {
  _layout = layout;
  const ov = ensureOverlay();
  const round = layout.round || layout.combat_round || '?';
  const turn  = layout.turn_label || 'Your turn';
  const playerHp = layout.player_hp ?? layout.hp ?? 0;
  const playerMax = layout.player_max_hp ?? layout.max_hp ?? playerHp;
  const enemies = numberEnemies(layout.enemies || []);
  const companions = layout.companions || [];
  const announcements = layout.move_announcements || layout.announcements || [];
  const slot = store.get('slot') || 'default';

  let html = `<div style="max-width:900px;margin:0 auto;">`;

  // Header
  html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
    <div style="color:#c8a84e;font-size:16px;letter-spacing:2px;">⚔ COMBAT</div>
    <div style="color:#6a6a7a;font-size:12px;">Round ${esc(String(round))} — ${esc(turn)}</div>
  </div>`;

  // Player HP
  const pPct = hpPct(playerHp, playerMax);
  html += `<div style="margin-bottom:18px;">
    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">
      <span style="color:#e8e8f0;">YOUR HP</span>
      <span style="color:#c44;">${playerHp} / ${playerMax}</span>
    </div>
    <div style="height:10px;background:#0a0a0f;border:1px solid #2a2a3a;border-radius:2px;">
      <div style="height:100%;width:${pPct}%;background:${pPct < 25 ? '#c44' : pPct < 50 ? '#e09040' : '#c44'};border-radius:1px;transition:width 0.5s;"></div>
    </div>
  </div>`;

  // Move announcements
  if (announcements.length > 0) {
    html += `<div style="margin-bottom:14px;padding:8px 12px;background:#12121e;border:1px solid #2a2a3a;font-size:11px;color:#6a6a7a;">`;
    html += `Actions: ${announcements.map(a => esc(a)).join(', ')}`;
    html += `</div>`;
  }

  // Enemy roster
  html += `<div style="margin-bottom:18px;"><div style="color:#8a7535;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Enemies</div>`;
  html += `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;">`;
  enemies.forEach((e, i) => {
    const eHp = e.hp ?? e.current_hp ?? 0;
    const eMax = e.max_hp ?? eHp || 1;
    const ePct = hpPct(eHp, eMax);
    const sel = i === _selectedIndex;
    html += `<div class="combat-enemy-card" data-idx="${i}"
      style="padding:12px;cursor:pointer;border:1px solid ${sel ? '#c8a84e' : '#2a2a3a'};
      background:${sel ? 'rgba(200,168,78,0.1)' : '#0c0c16'};border-radius:3px;transition:all 0.2s;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <span style="color:#e8e8f0;font-size:13px;">${esc(e.displayName)}</span>
        <span style="color:#6a6a7a;font-size:11px;">AC ${esc(String(e.ac ?? e.armor_class ?? '?'))}</span>
      </div>
      <div style="height:6px;background:#0a0a0f;border:1px solid #2a2a3a;border-radius:2px;">
        <div style="height:100%;width:${ePct}%;background:#c44;border-radius:1px;transition:width 0.5s;"></div>
      </div>
      <div style="font-size:10px;color:#6a6a7a;margin-top:3px;">${eHp} / ${eMax} HP</div>
    </div>`;
  });
  html += `</div></div>`;

  // Companions
  if (companions.length > 0) {
    html += `<div style="margin-bottom:18px;"><div style="color:#8a7535;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Companions</div>`;
    companions.forEach(c => {
      const cHp = c.hp ?? c.current_hp ?? 0;
      const cMax = c.max_hp ?? cHp;
      const cPct = hpPct(cHp, cMax);
      html += `<div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;">
          <span style="color:#e8e8f0;">${esc(c.name || 'Companion')}</span>
          <span style="color:#6a6a7a;">${cHp}/${cMax}</span>
        </div>
        <div style="height:5px;background:#0a0a0f;border:1px solid #2a2a3a;border-radius:2px;">
          <div style="height:100%;width:${cPct}%;background:#4CAF50;border-radius:1px;transition:width 0.5s;"></div>
        </div>
      </div>`;
    });
    html += `</div>`;
  }

  // Action buttons
  html += `<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;">`;
  const actions = [
    { label: '⚔ ATTACK', id: 'attack' },
    { label: '🛡 BLOCK', id: 'block' },
    { label: '🧪 ITEM', id: 'item' },
    { label: '👁 LOOK', id: 'look' },
    { label: '📢 ORDER', id: 'order', hidden: companions.length === 0 },
    { label: '🏃 FLEE', id: 'flee' },
  ];
  actions.forEach(a => {
    if (a.hidden) return;
    html += `<button class="btn combat-action-btn" data-action="${a.id}"
      style="flex:1;min-width:100px;padding:10px;font-size:12px;">${a.label}</button>`;
  });
  html += `</div>`;

  // Close
  html += `<div style="text-align:right;"><button class="btn btn-small" id="combat-close-btn">CLOSE OVERLAY</button></div>`;
  html += `</div>`;

  ov.innerHTML = html;
  ov.style.display = 'flex';

  // Bind events
  ov.querySelectorAll('.combat-enemy-card').forEach(card => {
    card.addEventListener('click', () => selectEnemy(parseInt(card.dataset.idx)));
  });
  ov.querySelectorAll('.combat-action-btn').forEach(btn => {
    btn.addEventListener('click', () => handleAction(btn.dataset.action));
  });
  const closeBtn = document.getElementById('combat-close-btn');
  if (closeBtn) closeBtn.addEventListener('click', closeCombat);
}

/* ── Actions ── */
function handleAction(act) {
  const slot = store.get('slot') || 'default';
  const enemies = _layout?.enemies || [];

  switch (act) {
    case 'attack': {
      if (_selectedIndex < 0 || _selectedIndex >= enemies.length) {
        toast('Select an enemy target first', 'warning');
        return;
      }
      const target = enemies[_selectedIndex];
      const name = target.name || target.displayName || 'enemy';
      doCmd(`/attack ${name}`, slot);
      break;
    }
    case 'block':
      doCmd('/block', slot);
      break;
    case 'item':
      doCmd('/use', slot);
      break;
    case 'look':
      doCmd('/look enemies', slot);
      break;
    case 'order': {
      const comps = _layout?.companions || [];
      if (comps.length === 0) { toast('No companions available', 'warning'); return; }
      doCmd(`/order ${comps[0].name || 'companion'} attack`, slot);
      break;
    }
    case 'flee':
      doCmd('/flee', slot);
      break;
  }
}

async function doCmd(cmd, slot) {
  try {
    const d = await action(cmd, { slot });
    store.emit('narration', d.narration);
    store.emit('layout', d.layout);
    store.emit('state', d.state);
    if (d.layout) {
      if (d.layout.combat_active) updateCombat(d.layout);
      else closeCombat();
    }
    checkDiceAnimation(d);
  } catch (e) {
    toast('Action failed: ' + e.message, 'error');
  }
}

function checkDiceAnimation(data) {
  if (!data) return;
  const roll = data.dice_roll ?? data.natural_roll ?? null;
  if (roll === 20) flashScreen('gold', '⚔ CRITICAL HIT!');
  else if (roll === 1) flashScreen('#c44', '✦ MISS!');
}

function flashScreen(color, text) {
  const ov = ensureOverlay();
  const flash = document.createElement('div');
  flash.style.cssText = `position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:${color};opacity:0;z-index:910;transition:opacity 0.15s;font-size:24px;color:#0a0a0f;font-weight:bold;letter-spacing:3px;pointer-events:none;`;
  flash.textContent = text;
  ov.appendChild(flash);
  requestAnimationFrame(() => {
    flash.style.opacity = '0.7';
    setTimeout(() => {
      flash.style.opacity = '0';
      setTimeout(() => flash.remove(), 300);
    }, 600);
  });
}

/* ── Public API ── */
export function openCombat(layout) {
  _selectedIndex = -1;
  render(layout);
}

export function closeCombat() {
  const ov = document.getElementById('combat-overlay');
  if (ov) ov.style.display = 'none';
}

export function selectEnemy(index) {
  _selectedIndex = index;
  if (_layout) render(_layout);
}

export function updateCombat(layout) {
  _layout = layout;
  render(layout);
}
