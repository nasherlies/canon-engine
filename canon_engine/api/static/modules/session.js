/* ═══ Session Management ═══ */
import * as api from './api.js';
import * as store from './store.js';
import * as logMod from './log.js';
import * as sidebar from './sidebar.js';
import * as toast from './toast.js';
import { $, html } from './dom.js';

export async function sendCommand(text) {
  // Show player input in log
  logMod.appendMessage(text, 'input');

  try {
    // Show loading indicator
    const loadId = logMod.showLoading();

    const response = await api.action(text);

    // Remove loading indicator
    logMod.removeLoading(loadId);

    handleResponse(response);
    return response;
  } catch (err) {
    logMod.appendMessage(`Error: ${err.message}`, 'system');
    toast.show(`Error: ${err.message}`, 'error');
    return null;
  }
}

export async function startCharacter(payload) {
  try {
    // Show loading
    const loadId = logMod.showLoading();

    const response = await api.startCharacter(payload);

    logMod.removeLoading(loadId);

    handleResponse(response);
    return response;
  } catch (err) {
    toast.show(`Failed to start: ${err.message}`, 'error');
    return null;
  }
}

export async function loadSave(slot) {
  try {
    const response = await api.loadSave(slot);
    handleResponse(response);
    return response;
  } catch (err) {
    toast.show(`Failed to load: ${err.message}`, 'error');
    return null;
  }
}

export async function quitGame() {
  try {
    const response = await api.quitGame();
    store.set('player', null);
    store.set('layout', null);
    return response;
  } catch (err) {
    toast.show(`Failed to quit: ${err.message}`, 'error');
    return null;
  }
}

export function handleResponse(data) {
  if (!data) return;

  // ── CRITICAL: Handle narration field from server ──
  // Server returns { narration, layout, state }
  if (data.narration) {
    logMod.appendMessage(data.narration, 'narration');
  }

  // Handle legacy message formats
  if (data.messages) {
    for (const msg of data.messages) {
      if (typeof msg === 'string') {
        logMod.appendMessage(msg, 'narration');
      } else if (msg && msg.text) {
        logMod.appendMessage(msg.text, msg.type || 'narration');
      }
    }
  }
  if (data.narrative) {
    logMod.appendMessage(data.narrative, 'narration');
  }
  if (data.description) {
    logMod.appendMessage(data.description, 'narration');
  }

  // Update layout
  if (data.layout) {
    store.set('layout', data.layout);
    applyLayout(data.layout);
  }

  // Update state
  if (data.state) {
    applyState(data.state);
  }

  // Toast notifications
  if (data.toast) {
    const t = typeof data.toast === 'string' ? { message: data.toast } : data.toast;
    toast.show(t.message, t.type || 'info');
  }

  // Combat state
  if (data.combat || data.in_combat) {
    store.set('combat', data.combat || true);
  } else if (data.combat === null || data.combat === false) {
    store.set('combat', null);
  }

  // Screen transitions based on response
  if (data.screen) {
    store.set('activeScreen', data.screen);
  }
}

export function applyState(state) {
  if (!state) return;

  // World state
  if (state.world) {
    const w = state.world;
    if (w.location_name || w.location_id) {
      const loc = w.location_name || w.location_id;
      const el = $('#t-loc');
      if (el) el.textContent = loc;
    }
  }

  // Player state
  if (state.player) {
    const p = state.player;
    // Update player name display
    if (p.name) {
      const nl = $('#t-name');
      if (nl) nl.textContent = `${p.name} · Lv ${p.level || 1}`;
    }
    // Update HP bar
    if (p.hp !== undefined && p.max_hp) {
      const hb = $('#b-hp');
      const hv = $('#v-hp');
      if (hb) hb.style.width = Math.round(p.hp / p.max_hp * 100) + '%';
      if (hv) hv.textContent = `${p.hp}/${p.max_hp}`;
    }
    // Update MP bar
    if (p.mp !== undefined && (p.max_mp || p.mp_max)) {
      const maxMp = p.max_mp || p.mp_max;
      const mb = $('#b-mp');
      const mv = $('#v-mp');
      if (mb) mb.style.width = Math.round(p.mp / maxMp * 100) + '%';
      if (mv) mv.textContent = `${p.mp}/${maxMp}`;
    }
    // Update STM bar
    if (p.stamina !== undefined && (p.max_stamina || p.stm_max)) {
      const maxStm = p.max_stamina || p.stm_max;
      const sb = $('#b-stm');
      const sv = $('#v-stm');
      if (sb) sb.style.width = Math.round(p.stamina / maxStm * 100) + '%';
      if (sv) sv.textContent = `${p.stamina}/${maxStm}`;
    }
    // Update stats grid
    if (p.stats) {
      renderStatsTopbar(p.stats);
    }
    // Update inventory
    if (p.inventory) {
      renderInvTopbar(p.inventory);
    }
    // Store player data
    store.set('player', p);
  }

  // Companions
  if (state.companions) {
    store.set('companions', state.companions);
  }
}

export function applyLayout(layout) {
  if (!layout) return;

  // Player data from layout.status
  if (layout.status) {
    const s = layout.status;
    const nl = $('#t-name');
    if (nl) nl.textContent = `${s.name || 'Adventurer'} · Lv ${s.level || 1}`;

    // HP bar
    if (s.hp !== undefined && s.max_hp) {
      const hb = $('#b-hp');
      const hv = $('#v-hp');
      if (hb) hb.style.width = Math.round(s.hp / s.max_hp * 100) + '%';
      if (hv) hv.textContent = `${s.hp}/${s.max_hp}`;
    }
    // MP bar
    if (s.mp !== undefined && s.max_mp) {
      const mb = $('#b-mp');
      const mv = $('#v-mp');
      if (mb) mb.style.width = Math.round(s.mp / s.max_mp * 100) + '%';
      if (mv) mv.textContent = `${s.mp}/${s.max_mp}`;
    }
    // STM bar
    if (s.stamina !== undefined && s.max_stamina) {
      const sb = $('#b-stm');
      const sv = $('#v-stm');
      if (sb) sb.style.width = Math.round(s.stamina / s.max_stamina * 100) + '%';
      if (sv) sv.textContent = `${s.stamina}/${s.max_stamina}`;
    }
    // Stats grid
    if (s.stats) {
      renderStatsTopbar(s.stats);
    }
    // Location
    if (s.location) {
      const tl = $('#t-loc');
      if (tl) tl.textContent = s.location;
    }
  }

  // Location from layout directly
  if (layout.location) {
    const loc = typeof layout.location === 'string' ? layout.location : layout.location.name;
    const el = $('#t-loc');
    if (el) el.textContent = loc;
  }

  // Inventory
  if (layout.inventory) {
    renderInvTopbar(layout.inventory);
  }

  // Companions
  if (layout.companions) {
    renderCompTopbar(layout.companions);
  }

  // Skills / abilities
  if (layout.abilities) {
    renderAbilities(layout.abilities);
  }

  // Quests
  if (layout.quests) {
    store.set('quests', layout.quests);
  }
}

// ── Topbar renderers ──

function renderStatsTopbar(st) {
  const g = $('#stats-grid');
  if (!g) return;
  let h = '';
  ['STR', 'DEX', 'INT', 'CHA', 'CON', 'LCK'].forEach(s => {
    const v = st[s] || 10;
    const m = Math.floor((v - 10) / 2);
    const sg = m >= 0 ? '+' : '';
    h += `<div class="stat"><div class="sn">${s}</div><div class="sv">${v}</div><div class="sm">${sg}${m}</div></div>`;
  });
  g.innerHTML = h;
}

function renderCompTopbar(companions) {
  // Update companion count badge
  const count = companions ? companions.length : 0;
  sidebar.updateBadges({ party: count });
}

function renderInvTopbar(items) {
  const count = items ? items.length : 0;
  sidebar.updateBadges({ inventory: count });
}

function renderAbilities(abilities) {
  const el = $('#abil-list');
  if (!el) return;
  if (!abilities || !abilities.length) {
    el.innerHTML = '<span class="empty">No abilities</span>';
    return;
  }
  el.innerHTML = abilities.map(a => {
    const name = typeof a === 'string' ? a : (a.name || '?');
    const desc = typeof a === 'object' && a.description ? a.description : '';
    return `<div class="ability-card"><div class="ab-name">${esc(name)}</div>${desc ? `<div class="ab-desc">${esc(desc)}</div>` : ''}</div>`;
  }).join('');
}

function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
