// factions.js — Faction Panel
// Canon Engine UI Module

import { show as showToast } from './toast.js';
import { get as getState, set as setState } from './store.js';

const TIER_THRESHOLDS = [
  { min: -100, max: -80, label: 'Hated', color: '#cc3333', shopMod: 150 },
  { min: -80, max: -40, label: 'Hostile', color: '#cc6633', shopMod: 130 },
  { min: -40, max: -10, label: 'Unfriendly', color: '#886633', shopMod: 110 },
  { min: -10, max: 10, label: 'Neutral', color: '#666666', shopMod: 100 },
  { min: 10, max: 40, label: 'Friendly', color: '#33aa33', shopMod: 90 },
  { min: 40, max: 80, label: 'Allied', color: '#33aa66', shopMod: 80 },
  { min: 80, max: 101, label: 'Honored', color: '#c8b16c', shopMod: 70 }
];

let _overlay = null;
let _layout = null;

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function getTier(rep) {
  for (const tier of TIER_THRESHOLDS) {
    if (rep >= tier.min && rep < tier.max) return tier;
  }
  return TIER_THRESHOLDS[3]; // default neutral
}

function createOverlay() {
  if (_overlay) return _overlay;
  const overlay = document.createElement('div');
  overlay.id = 'factions-overlay';
  overlay.className = 'modal';
  overlay.style.zIndex = '105';
  overlay.innerHTML = `
    <div class="modal-box" style="width:520px;max-height:85dvh;">
      <button class="close-btn" id="factions-close">&times;</button>
      <h2>🏴 FACTIONS</h2>
      <div id="factions-body" style="overflow-y:auto;max-height:70dvh;"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector('#factions-close').addEventListener('click', closeFactions);
  overlay.addEventListener('mousedown', (e) => {
    if (e.target === overlay) closeFactions();
  });

  _overlay = overlay;
  return overlay;
}

function renderFactionCard(faction, index) {
  const rep = faction.reputation !== undefined ? faction.reputation : faction.rep || 0;
  const tier = faction.tier ? TIER_THRESHOLDS.find(t => t.label.toLowerCase() === faction.tier.toLowerCase()) || getTier(rep) : getTier(rep);
  const repPct = Math.round((rep + 100) / 2); // map -100..100 to 0..100
  const shopMod = faction.shop_modifier || faction.shopMod || tier.shopMod;
  const isNemesis = tier.label === 'Hated' || faction.nemesis;

  let html = `<div class="faction-card" style="
    background:rgba(26,26,46,0.7);border:1px solid rgba(58,58,92,0.3);
    padding:12px;margin-bottom:10px;
    ${isNemesis ? 'border-left:3px solid #cc3333;' : ''}
  ">`;

  // Header
  html += `<div style="display:flex;justify-content:space-between;align-items:center;">`;
  html += `<div style="color:#c8b16c;font-size:15px;font-weight:bold;">${esc(faction.name || 'Unknown Faction')}</div>`;
  html += `<span style="
    background:${tier.color};color:#000;font-size:10px;font-weight:bold;
    padding:2px 8px;letter-spacing:1px;
  ">${tier.label.toUpperCase()}</span>`;
  html += `</div>`;

  // Description
  if (faction.description) {
    html += `<div style="color:#888;font-size:12px;margin-top:6px;line-height:1.4;">${esc(faction.description)}</div>`;
  }

  // Reputation bar
  html += `<div style="margin-top:8px;">`;
  html += `<div style="display:flex;justify-content:space-between;font-size:11px;color:#555;">`;
  html += `<span>Rep: ${rep}</span>`;
  html += `<span>${tier.label}</span>`;
  html += `</div>`;
  html += `<div style="height:8px;background:var(--bg,#0a0a0a);border:1px solid rgba(58,58,92,0.3);margin-top:2px;overflow:hidden;">`;
  html += `<div style="height:100%;width:${Math.max(0, Math.min(100, repPct))}%;background:${tier.color};transition:width 0.4s;"></div>`;
  html += `</div>`;
  html += `</div>`;

  // Shop modifier
  if (shopMod !== undefined) {
    const priceColor = shopMod > 100 ? '#cc6633' : (shopMod < 100 ? '#33aa33' : '#666');
    html += `<div style="margin-top:6px;display:flex;justify-content:space-between;align-items:center;">`;
    html += `<span style="color:#555;font-size:12px;">Shop Prices:</span>`;
    html += `<span style="color:${priceColor};font-size:13px;font-weight:bold;">${shopMod}%</span>`;
    html += `</div>`;
  }

  // Nemesis warning
  if (isNemesis) {
    html += `<div style="
      margin-top:8px;padding:6px 10px;background:rgba(204,51,51,0.1);
      border:1px solid rgba(204,51,51,0.3);color:#cc3333;font-size:11px;
      display:flex;align-items:center;gap:6px;
    ">`;
    html += `<span>⚠</span> <span>Nemesis — This faction will attack on sight!</span>`;
    html += `</div>`;
  }

  html += `</div>`;
  return html;
}

function renderLayout(layout) {
  _layout = layout || {};
  const body = _overlay.querySelector('#factions-body');
  if (!body) return;

  const factions = layout.factions || layout.faction || [];
  if (!factions.length) {
    body.innerHTML = '<div style="text-align:center;color:#555;padding:40px;font-style:italic;">No faction standings yet. Interact with factions to build reputation.</div>';
    return;
  }

  body.innerHTML = factions.map((f, i) => renderFactionCard(f, i)).join('');
}

export function openFactions(layout) {
  _layout = layout || {};
  createOverlay();
  renderLayout(_layout);
  _overlay.classList.add('show');
}

export function closeFactions() {
  if (_overlay) _overlay.classList.remove('show');
}

export default { openFactions, closeFactions };
