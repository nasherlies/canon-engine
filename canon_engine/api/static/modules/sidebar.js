/* ═══ Sidebar Management ═══ */
import { $, html } from './dom.js';
import * as store from './store.js';

const panes = {};

function getPanes() {
  panes.stats = $('#pane-stats');
  panes.inventory = $('#pane-inventory');
  panes.party = $('#pane-party');
  panes.skills = $('#pane-skills');
  panes.quests = $('#pane-quests');
}

export function init() {
  getPanes();
  // Init tabs
  document.addEventListener('click', (e) => {
    const tab = e.target.closest('.sidebar-tab, .mobile-nav-btn');
    if (tab && tab.dataset.tab) {
      switchTab(tab.dataset.tab);
    }
  });
}

export function switchTab(name) {
  store.set('activeSidebarTab', name);

  // Update tab buttons
  document.querySelectorAll('.sidebar-tab, .mobile-nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === name);
  });

  // Update panes
  document.querySelectorAll('.sidebar-pane').forEach(pane => {
    pane.classList.toggle('active', pane.id === `pane-${name}`);
  });
}

export function renderStats(player) {
  if (!panes.stats) getPanes();
  if (!panes.stats || !player) return;

  const hpPct = player.hp_max ? Math.round((player.hp / player.hp_max) * 100) : 0;
  const mpPct = player.mp_max ? Math.round((player.mp / player.mp_max) * 100) : 0;
  const stmPct = player.stm_max ? Math.round((player.stm / player.stm_max) * 100) : 0;
  const xpPct = player.xp_max ? Math.round((player.xp / player.xp_max) * 100) : 0;

  let statsGrid = '';
  const statNames = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
  for (const s of statNames) {
    if (player[s] !== undefined) {
      statsGrid += `<div class="stat-item"><span class="stat-item-label">${s.toUpperCase()}</span><span class="stat-item-value">${player[s]}</span></div>`;
    }
  }

  panes.stats.innerHTML = `
    <div class="stat-card">
      <div class="card-title">Level ${player.level || 1} ${player.class || ''}</div>
      <div class="card-subtitle">${player.race || ''}</div>
    </div>
    <div class="stat-bar">
      <div class="stat-bar-label"><span>HP</span><span>${player.hp || 0}/${player.hp_max || 0}</span></div>
      <div class="stat-bar-track"><div class="stat-bar-fill hp${hpPct <= 25 ? ' low-hp' : ''}" style="width:${hpPct}%"></div></div>
    </div>
    <div class="stat-bar">
      <div class="stat-bar-label"><span>MP</span><span>${player.mp || 0}/${player.mp_max || 0}</span></div>
      <div class="stat-bar-track"><div class="stat-bar-fill mp" style="width:${mpPct}%"></div></div>
    </div>
    <div class="stat-bar">
      <div class="stat-bar-label"><span>STM</span><span>${player.stm || 0}/${player.stm_max || 0}</span></div>
      <div class="stat-bar-track"><div class="stat-bar-fill stm" style="width:${stmPct}%"></div></div>
    </div>
    <div class="stat-bar">
      <div class="stat-bar-label"><span>XP</span><span>${player.xp || 0}/${player.xp_max || 0} (${xpPct}%)</span></div>
      <div class="stat-bar-track"><div class="stat-bar-fill xp" style="width:${xpPct}%"></div></div>
    </div>
    ${statsGrid ? `<div class="stat-grid">${statsGrid}</div>` : ''}
  `;
}

export function renderInventory(items) {
  if (!panes.inventory) getPanes();
  if (!panes.inventory) return;

  if (!items || items.length === 0) {
    panes.inventory.innerHTML = '<p class="card-subtitle" style="text-align:center;padding:20px;">Empty inventory</p>';
    return;
  }

  panes.inventory.innerHTML = items.map(item => `
    <div class="item-card" data-item="${esc(item.name || item.id || '')}">
      <div>
        <div class="card-title">${esc(item.name || 'Unknown')}</div>
        ${item.description ? `<div class="card-desc">${esc(item.description)}</div>` : ''}
      </div>
      ${item.quantity && item.quantity > 1 ? `<span class="item-qty">×${item.quantity}</span>` : ''}
    </div>
  `).join('');
}

export function renderCompanions(companions) {
  if (!panes.party) getPanes();
  if (!panes.party) return;

  if (!companions || companions.length === 0) {
    panes.party.innerHTML = '<p class="card-subtitle" style="text-align:center;padding:20px;">No companions</p>';
    return;
  }

  panes.party.innerHTML = companions.map(c => `
    <div class="companion-card">
      <div class="card-title">${esc(c.name || 'Unknown')}</div>
      <div class="card-subtitle">${esc(c.class || '')} · Lv ${c.level || '?'}</div>
      ${c.description ? `<div class="card-desc">${esc(c.description)}</div>` : ''}
    </div>
  `).join('');
}

export function renderSkills(skills) {
  if (!panes.skills) getPanes();
  if (!panes.skills) return;

  if (!skills || skills.length === 0) {
    panes.skills.innerHTML = '<p class="card-subtitle" style="text-align:center;padding:20px;">No skills learned</p>';
    return;
  }

  panes.skills.innerHTML = skills.map(s => `
    <div class="skill-card">
      <div class="card-title">${esc(s.name || 'Unknown')}</div>
      ${s.rank !== undefined ? `<span class="skill-rank">Rank ${s.rank}</span>` : ''}
      ${s.description ? `<div class="card-desc">${esc(s.description)}</div>` : ''}
    </div>
  `).join('');
}

export function renderQuests(quests) {
  if (!panes.quests) getPanes();
  if (!panes.quests) return;

  if (!quests || quests.length === 0) {
    panes.quests.innerHTML = '<p class="card-subtitle" style="text-align:center;padding:20px;">No active quests</p>';
    return;
  }

  const active = quests.filter(q => q.status === 'active');
  const completed = quests.filter(q => q.status === 'completed');
  const failed = quests.filter(q => q.status === 'failed');

  let html_str = '';
  if (active.length) {
    html_str += '<div class="quest-section-title">Active</div>';
    html_str += active.map(q => questCard(q)).join('');
  }
  if (completed.length) {
    html_str += '<div class="quest-section-title">Completed</div>';
    html_str += completed.map(q => questCard(q)).join('');
  }
  if (failed.length) {
    html_str += '<div class="quest-section-title">Failed</div>';
    html_str += failed.map(q => questCard(q)).join('');
  }

  panes.quests.innerHTML = html_str;
}

function questCard(q) {
  return `<div class="quest-card ${q.status || 'active'}">
    <div class="card-title">${esc(q.name || q.title || 'Unknown Quest')}</div>
    ${q.description ? `<div class="card-desc">${esc(q.description)}</div>` : ''}
  </div>`;
}

export function updateBadges(counts) {
  for (const [tab, count] of Object.entries(counts || {})) {
    const tabs = document.querySelectorAll(`.sidebar-tab[data-tab="${tab}"], .mobile-nav-btn[data-tab="${tab}"]`);
    tabs.forEach(btn => {
      let badge = btn.querySelector('.badge');
      if (count > 0) {
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'badge';
          btn.appendChild(badge);
        }
        badge.textContent = count;
      } else if (badge) {
        badge.remove();
      }
    });
  }
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
