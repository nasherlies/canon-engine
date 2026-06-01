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
    const response = await api.action(text);
    handleResponse(response);
    return response;
  } catch (err) {
    logMod.appendMessage(`Error: ${err.message}`, 'system');
    return null;
  }
}

export async function startCharacter(payload) {
  try {
    const response = await api.startCharacter(payload);
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

  // Update layout
  if (data.layout) {
    store.set('layout', data.layout);
    applyLayout(data.layout);
  }

  // Handle narrative messages
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

export function applyLayout(layout) {
  if (!layout) return;

  // Player data
  if (layout.player) {
    store.set('player', layout.player);
    updateTopbar(layout.player);
    sidebar.renderStats(layout.player);
  }

  // Location
  if (layout.location) {
    const loc = typeof layout.location === 'string' ? layout.location : layout.location.name;
    const el = $('#location-text');
    if (el) el.textContent = loc;
  }

  // Inventory
  if (layout.inventory) {
    sidebar.renderInventory(layout.inventory);
  }

  // Companions
  if (layout.companions) {
    sidebar.renderCompanions(layout.companions);
  }

  // Skills
  if (layout.skills) {
    sidebar.renderSkills(layout.skills);
  }

  // Quests
  if (layout.quests) {
    store.set('quests', layout.quests);
    sidebar.renderQuests(layout.quests);
  }

  // Combat
  if (layout.combat) {
    store.set('combat', layout.combat);
  }
}

function updateTopbar(player) {
  const nameEl = $('#player-name');
  const levelEl = $('#player-level');
  const hpFill = $('#hp-fill');
  const mpFill = $('#mp-fill');
  const xpFill = $('#xp-fill');
  const hpLabel = $('#hp-label');
  const mpLabel = $('#mp-label');
  const xpLabel = $('#xp-label');

  if (nameEl) nameEl.textContent = player.name || 'Hero';
  if (levelEl) levelEl.textContent = `Lv ${player.level || 1}`;

  const hpPct = player.hp_max ? (player.hp / player.hp_max) * 100 : 0;
  const mpPct = player.mp_max ? (player.mp / player.mp_max) * 100 : 0;
  const xpPct = player.xp_max ? (player.xp / player.xp_max) * 100 : 0;

  if (hpFill) {
    hpFill.style.width = `${hpPct}%`;
    hpFill.classList.toggle('low-hp', hpPct <= 25);
  }
  if (mpFill) mpFill.style.width = `${mpPct}%`;
  if (xpFill) xpFill.style.width = `${xpPct}%`;

  if (hpLabel) hpLabel.textContent = `${player.hp || 0}/${player.hp_max || 0}`;
  if (mpLabel) mpLabel.textContent = `${player.mp || 0}/${player.mp_max || 0}`;
  if (xpLabel) xpLabel.textContent = `${Math.round(xpPct)}%`;
}
