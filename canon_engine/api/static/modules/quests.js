// quests.js — Quest Log Overlay
// Canon Engine UI Module

import { showToast } from './toast.js';
import { getState, setState } from './store.js';

const PULSE_MAP = {
  'NEW QUEST': { icon: '📜', color: '#c8b16c' },
  'QUEST COMPLETE': { icon: '✅', color: '#33aa33' },
  'QUEST FAILED': { icon: '❌', color: '#cc3333' }
};

let _overlay = null;
let _layout = null;

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function createOverlay() {
  if (_overlay) return _overlay;
  const overlay = document.createElement('div');
  overlay.id = 'quests-overlay';
  overlay.className = 'modal';
  overlay.style.zIndex = '105';
  overlay.innerHTML = `
    <div class="modal-box" style="width:560px;max-height:85dvh;">
      <button class="close-btn" id="quests-close">&times;</button>
      <h2>📜 QUEST LOG</h2>
      <div id="quests-body" style="overflow-y:auto;max-height:70dvh;"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector('#quests-close').addEventListener('click', closeQuests);
  overlay.addEventListener('mousedown', (e) => {
    if (e.target === overlay) closeQuests();
  });

  _overlay = overlay;
  return overlay;
}

function renderQuestSection(quests, sectionKey, borderLabel, borderColor, expanded, strikethrough) {
  if (!quests || quests.length === 0) return '';
  const toggleIcon = expanded ? '▼' : '▶';
  let html = `<div class="quest-section" style="margin-bottom:12px;">`;
  html += `<div class="quest-section-header" data-section="${sectionKey}" style="
    display:flex;align-items:center;gap:8px;padding:8px 12px;
    border:2px solid ${borderColor};border-bottom:${expanded ? 'none' : '2px solid ' + borderColor};
    cursor:pointer;background:rgba(26,26,46,0.5);
  ">`;
  html += `<span style="color:${borderColor};font-size:12px;">${toggleIcon}</span>`;
  html += `<span style="color:${borderColor};font-size:12px;letter-spacing:2px;font-weight:bold;">${borderLabel}</span>`;
  html += `<span style="color:#666;font-size:11px;">(${quests.length})</span>`;
  html += `</div>`;

  if (expanded) {
    html += `<div style="border:2px solid ${borderColor};border-top:none;padding:8px;">`;
    quests.forEach((q, i) => {
      html += renderQuestCard(q, strikethrough, borderColor, i);
    });
    html += `</div>`;
  }
  html += `</div>`;
  return html;
}

function renderQuestCard(quest, strikethrough, borderColor, index) {
  const titleStyle = strikethrough ? 'text-decoration:line-through;opacity:0.6;' : '';
  const cardBg = strikethrough ? 'rgba(26,26,46,0.3)' : 'rgba(26,26,46,0.7)';

  let html = `<div class="quest-card" style="
    background:${cardBg};border:1px solid rgba(58,58,92,0.3);
    padding:12px;margin-bottom:8px;
    border-left:3px solid ${borderColor};
  ">`;
  html += `<div style="display:flex;justify-content:space-between;align-items:center;">`;
  html += `<div style="color:#c8b16c;font-size:14px;font-weight:bold;${titleStyle}">${esc(quest.title || 'Unknown Quest')}</div>`;
  if (quest.giver) {
    html += `<div style="color:#666;font-size:11px;">Giver: ${esc(quest.giver)}</div>`;
  }
  html += `</div>`;

  if (quest.description) {
    html += `<div style="color:#888;font-size:12px;margin-top:4px;${titleStyle}">${esc(quest.description)}</div>`;
  }

  if (quest.objectives && quest.objectives.length > 0) {
    html += `<div style="margin-top:8px;">`;
    quest.objectives.forEach(obj => {
      const done = obj.done || obj.completed;
      const icon = done ? '✓' : '·';
      const iconColor = done ? '#33aa33' : '#666';
      const textStyle = strikethrough ? 'text-decoration:line-through;opacity:0.5;' : (done ? 'text-decoration:line-through;opacity:0.7;' : '');
      html += `<div style="display:flex;gap:8px;align-items:baseline;padding:2px 0;">`;
      html += `<span style="color:${iconColor};font-weight:bold;min-width:12px;">${icon}</span>`;
      html += `<span style="color:${done ? '#666' : '#a3a3a3'};font-size:13px;${textStyle}">${esc(obj.text || obj.description || obj)}</span>`;
      html += `</div>`;
    });
    html += `</div>`;
  }

  html += `</div>`;
  return html;
}

function renderLayout(layout) {
  const body = _overlay.querySelector('#quests-body');
  if (!body) return;

  const active = layout.quests_active || layout.active || [];
  const completed = layout.quests_completed || layout.completed || [];
  const failed = layout.quests_failed || layout.failed || [];

  let html = '';
  html += renderQuestSection(active, 'active', 'ACTIVE', '#c8b16c', true, false);
  html += renderQuestSection(completed, 'completed', 'COMPLETED', '#33aa33', false, true);
  html += renderQuestSection(failed, 'failed', 'FAILED', '#cc3333', false, true);

  if (!active.length && !completed.length && !failed.length) {
    html = '<div style="text-align:center;color:#555;padding:40px;font-style:italic;">No quests yet. Explore the world to discover quests!</div>';
  }

  body.innerHTML = html;

  // Collapsible sections
  body.querySelectorAll('.quest-section-header').forEach(header => {
    header.addEventListener('click', () => {
      const section = header.parentElement;
      const content = header.nextElementSibling;
      if (content && content.tagName !== 'DIV') return;
      if (content) {
        const isHidden = content.style.display === 'none';
        content.style.display = isHidden ? 'block' : 'none';
        const icon = header.querySelector('span:first-child');
        if (icon) icon.textContent = isHidden ? '▼' : '▶';
      }
    });
  });
}

export function openQuests(layout) {
  _layout = layout || {};
  createOverlay();
  renderLayout(_layout);
  _overlay.classList.add('show');
}

export function closeQuests() {
  if (_overlay) _overlay.classList.remove('show');
}

export function updateQuestPulse(pulse) {
  if (!pulse || !pulse.type) return;
  const info = PULSE_MAP[pulse.type];
  if (!info) return;

  const message = pulse.message || pulse.type;
  if (typeof showToast === 'function') {
    showToast(message, { icon: info.icon, color: info.color, duration: 4000 });
  }

  // Update store state
  if (pulse.quest && typeof setState === 'function') {
    const quests = getState('quests') || [];
    if (pulse.type === 'NEW QUEST') {
      quests.push(pulse.quest);
    } else if (pulse.type === 'QUEST COMPLETE' || pulse.type === 'QUEST FAILED') {
      const idx = quests.findIndex(q => q.id === pulse.quest.id || q.title === pulse.quest.title);
      if (idx >= 0) {
        quests[idx] = { ...quests[idx], ...pulse.quest, status: pulse.type === 'QUEST COMPLETE' ? 'completed' : 'failed' };
      }
    }
    setState('quests', quests);
  }
}

export default { openQuests, closeQuests, updateQuestPulse };
