/* ═══ Sidebar Management ═══ */
import { $, html } from './dom.js';
import * as store from './store.js';

const panes = {};

function getPanes() {
  // Match actual HTML pane IDs
  panes.stats = $('#pane-stats');
  panes.inventory = $('#pane-inv');
  panes.party = $('#pane-comp');
  panes.skills = $('#pane-abil');
  panes.quests = $('#pane-journal');
}

export function init() {
  getPanes();
  // Init tabs — match actual HTML class .side-tab
  document.addEventListener('click', (e) => {
    const tab = e.target.closest('.side-tab, .mobile-nav-btn');
    if (tab) {
      // Determine tab index from position
      const allTabs = document.querySelectorAll('.side-tab');
      const idx = Array.from(allTabs).indexOf(tab);
      if (idx >= 0) {
        const tabNames = ['stats', 'inventory', 'party', 'skills', 'quests'];
        switchTab(tabNames[idx]);
      }
    }
  });
}

export function switchTab(name) {
  store.set('activeSidebarTab', name);

  const tabNames = ['stats', 'inventory', 'party', 'skills', 'quests'];
  const idx = tabNames.indexOf(name);

  // Update tab buttons
  document.querySelectorAll('.side-tab').forEach((btn, i) => {
    btn.classList.toggle('active', i === idx);
  });

  // Update panes
  document.querySelectorAll('.side-pane').forEach((pane, i) => {
    pane.classList.toggle('show', i === idx);
  });
}

export function renderStats(player) {
  if (!panes.stats) getPanes();
  if (!panes.stats || !player) return;

  const hpPct = player.hp_max || player.max_hp ? Math.round((player.hp / (player.hp_max || player.max_hp)) * 100) : 0;
  const mpPct = player.mp_max ? Math.round((player.mp / player.mp_max) * 100) : 0;
  const stmPct = player.stm_max || player.max_stamina ? Math.round((player.stamina || player.stm || 0) / (player.stm_max || player.max_stamina || 1) * 100) : 0;
  const xpPct = player.xp_next || player.xp_max ? Math.round((player.xp || 0) / (player.xp_next || player.xp_max || 1) * 100) : 0;

  let statsGrid = '';
  // Handle both uppercase (STR/DEX/etc) and lowercase (strength/dexterity) stat names
  const stats = player.stats || player;
  const statNames = [
    ['STR', stats.STR || stats.strength],
    ['DEX', stats.DEX || stats.dexterity],
    ['CON', stats.CON || stats.constitution],
    ['INT', stats.INT || stats.intelligence],
    ['WIS', stats.WIS || stats.wisdom],
    ['CHA', stats.CHA || stats.charisma],
  ];
  for (const [name, val] of statNames) {
    if (val !== undefined) {
      const mod = Math.floor((val - 10) / 2);
      const sign = mod >= 0 ? '+' : '';
      statsGrid += `<div class="stat-cell"><div class="sc-name">${name}</div><div class="sc-val">${val}</div><div class="sm">${sign}${mod}</div></div>`;
    }
  }

  const maxHp = player.hp_max || player.max_hp || 0;
  const maxMp = player.mp_max || 0;
  const maxStm = player.stm_max || player.max_stamina || 0;
  const xpNext = player.xp_next || player.xp_max || 0;

  panes.stats.innerHTML = `
    <div class="stat-card">
      <div class="card-title">Level ${player.level || 1} ${player.class || player.class_name || player.archetype || ''}</div>
      <div class="card-subtitle">${player.race || ''}</div>
    </div>
    <div class="bar"><span class="bl">HP</span><div class="bt"><div class="bf hp${hpPct <= 25 ? ' low-hp' : ''}" style="width:${hpPct}%"></div><span class="bv">${player.hp || 0}/${maxHp}</span></div></div>
    <div class="bar"><span class="bl">MP</span><div class="bt"><div class="bf mp" style="width:${mpPct}%"></div><span class="bv">${player.mp || 0}/${maxMp}</span></div></div>
    <div class="bar"><span class="bl">STM</span><div class="bt"><div class="bf stm" style="width:${stmPct}%"></div><span class="bv">${player.stamina || player.stm || 0}/${maxStm}</span></div></div>
    <div class="bar"><span class="bl">XP</span><div class="bt"><div class="bf stm" style="width:${xpPct}%"></div><span class="bv">${player.xp || 0}/${xpNext} (${xpPct}%)</span></div></div>
    ${statsGrid ? `<div class="stat-grid">${statsGrid}</div>` : ''}
  `;
}

export function renderInventory(items) {
  if (!panes.inventory) getPanes();
  if (!panes.inventory) return;

  if (!items || items.length === 0) {
    panes.inventory.innerHTML = '<span class="empty">Empty</span>';
    return;
  }

  panes.inventory.innerHTML = items.map(item => {
    const name = typeof item === 'string' ? item : (item.name || 'Unknown');
    const qty = (typeof item === 'object' ? (item.quantity || item.qty) : 1) || 1;
    const rarity = (typeof item === 'object' ? item.rarity : '') || 'common';
    return `<div class="inv-item"><div><b>${esc(name)}</b> <span style="color:#555">[${esc(rarity)}]</span></div>${qty > 1 ? `<span style="color:#6a6a7a;font-size:10px;">×${qty}</span>` : ''}</div>`;
  }).join('');
}

export function renderCompanions(companions) {
  if (!panes.party) getPanes();
  if (!panes.party) return;

  if (!companions || companions.length === 0) {
    panes.party.innerHTML = '<span class="empty">No companions</span>';
    return;
  }

  panes.party.innerHTML = companions.map(c => {
    const loyalty = c.loyalty || 50;
    return `<div class="comp-card">
      <div class="comp-portrait">${c.name ? c.name[0] : '?'}</div>
      <div class="comp-name">${esc(c.name || 'Unknown')}</div>
      <div class="comp-info">${esc(c.race || '')} ${esc(c.class_name || c.class || '')} · HP ${c.hp || '?'}/${c.max_hp || '?'}</div>
      <div class="loyalty-bar"><div class="loyalty-fill" style="width:${loyalty}%"></div></div>
      <div style="font-size:11px;color:#555;margin-top:2px">Loyalty: ${loyalty}%</div>
    </div>`;
  }).join('');
}

export function renderSkills(skills) {
  if (!panes.skills) getPanes();
  if (!panes.skills) return;

  if (!skills || skills.length === 0) {
    panes.skills.innerHTML = '<span class="empty">No abilities</span>';
    return;
  }

  panes.skills.innerHTML = skills.map(s => {
    const name = typeof s === 'string' ? s : (s.name || 'Unknown');
    const desc = typeof s === 'object' && s.description ? s.description : '';
    const cd = typeof s === 'object' && s.cooldown ? s.cooldown : '';
    return `<div class="ability-card">
      <div class="ab-name">${esc(name)}</div>
      ${desc ? `<div class="ab-desc">${esc(desc)}</div>` : ''}
      ${cd ? `<div class="ab-cd">Cooldown: ${esc(cd)}</div>` : ''}
    </div>`;
  }).join('');
}

export function renderQuests(quests) {
  if (!panes.quests) getPanes();
  if (!panes.quests) return;

  if (!quests || quests.length === 0) {
    panes.quests.innerHTML = '<span class="empty">No entries yet.</span>';
    return;
  }

  panes.quests.innerHTML = quests.slice().reverse().map(q => {
    return `<div class="journal-entry">
      <div class="je-title">${esc(q.name || q.title || 'Event')}</div>
      <div class="je-text">${esc(q.description || q.text || '')}</div>
    </div>`;
  }).join('');
}

export function updateBadges(counts) {
  const badgeMap = {
    stats: 'badge-stats',
    inventory: 'badge-inv',
    party: 'badge-comp',
    skills: 'badge-abil',
    quests: 'badge-journal',
  };
  for (const [tab, count] of Object.entries(counts || {})) {
    const badgeId = badgeMap[tab];
    if (!badgeId) continue;
    const b = document.getElementById(badgeId);
    if (!b) continue;
    if (count > 0) {
      b.textContent = count;
      b.classList.add('show');
    } else {
      b.classList.remove('show');
    }
  }
}

function esc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
