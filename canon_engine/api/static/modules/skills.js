// ─── skills.js ─── Skill Tree Overlay ───
import { apiPost } from './api.js';
import { get as getState, set as setState } from './store.js';
import { show as toast } from './toast.js';

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

const BRANCH_COLORS = {
  warrior: '#c44',
  rogue:   '#4CAF50',
  mage:    '#2196F3',
  ranger:  '#e8c86e'
};

let _layout = null;

/* ── Overlay ── */
function ensureOverlay() {
  let ov = document.getElementById('skills-overlay');
  if (ov) return ov;
  ov = document.createElement('div');
  ov.id = 'skills-overlay';
  ov.style.cssText = `
    position:fixed;inset:0;z-index:800;display:none;
    background:rgba(0,0,0,0.92);overflow-y:auto;
    font-family:'Cascadia Mono','Fira Code',monospace;
    padding:20px;color:#c8c8d0;
  `;
  document.body.appendChild(ov);
  return ov;
}

/* ── Render ── */
function render(layout) {
  _layout = layout;
  const ov = ensureOverlay();
  const skillTree = layout.skill_tree || layout.skills || {};
  const branches = skillTree.branches || [];
  const skillPoints = layout.skill_points ?? skillTree.skill_points ?? getState('skill_points') ?? 0;

  let html = `<div style="max-width:1000px;margin:0 auto;">`;
  html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
    <div style="color:#c8a84e;font-size:16px;letter-spacing:2px;">✦ SKILL TREE</div>
    <div style="display:flex;align-items:center;gap:16px;">
      <span style="color:#c8a84e;font-size:13px;">Skill Points: <strong>${skillPoints}</strong></span>
      <button class="btn btn-small" id="skills-close-btn">CLOSE</button>
    </div>
  </div>`;

  if (branches.length === 0) {
    // Flat skill list fallback
    const skills = layout.skill_list || skillTree.skills || [];
    if (skills.length === 0) {
      html += `<div style="color:#6a6a7a;font-size:12px;padding:20px;text-align:center;">No skills available</div>`;
    } else {
      html += `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;">`;
      skills.forEach(skill => {
        html += renderSkillNode(skill, '#c8a84e');
      });
      html += `</div>`;
    }
  } else {
    // Render branches
    branches.forEach(branch => {
      const branchName = (branch.name || branch.id || 'unknown').toLowerCase();
      const color = BRANCH_COLORS[branchName] || '#c8a84e';
      const skills = branch.skills || [];

      html += `<div style="margin-bottom:24px;">
        <div style="color:${color};font-size:13px;text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;padding-bottom:4px;border-bottom:1px solid ${color}33;">
          ${esc(branch.name || branch.id)}
        </div>
        <div style="position:relative;padding-left:20px;">`;

      // Draw connecting lines (vertical spine)
      if (skills.length > 1) {
        html += `<div style="position:absolute;left:8px;top:0;bottom:0;width:1px;background:${color}33;"></div>`;
      }

      skills.forEach((skill, i) => {
        // Horizontal connector
        html += `<div style="position:absolute;left:4px;top:${i * 90 + 30}px;width:9px;height:1px;background:${color}33;"></div>`;
        html += `<div style="margin-bottom:10px;">${renderSkillNode(skill, color)}</div>`;
      });

      html += `</div></div>`;
    });
  }

  html += `</div>`;
  ov.innerHTML = html;
  ov.style.display = 'flex';

  // Bind events
  ov.querySelectorAll('.skill-unlock-btn').forEach(btn => {
    btn.addEventListener('click', () => unlockSkill(btn.dataset.skill));
  });
  ov.querySelectorAll('.skill-use-btn').forEach(btn => {
    btn.addEventListener('click', () => useSkill(btn.dataset.skill));
  });
  const closeBtn = document.getElementById('skills-close-btn');
  if (closeBtn) closeBtn.addEventListener('click', closeSkills);
}

function renderSkillNode(skill, branchColor) {
  const name = skill.name || skill.id || 'Skill';
  const desc = skill.description || skill.desc || '';
  const locked = skill.locked ?? !skill.unlocked;
  const available = skill.available ?? (skill.points_required <= (_layout?.skill_points ?? 0) && locked);
  const passive = skill.passive || skill.type === 'passive';
  const cost = skill.cost || skill.points_required || 1;
  const skillId = skill.id || skill.name;

  const borderColor = locked ? '#2a2a3a' : branchColor;
  const bgColor = locked ? '#0c0c16' : (passive ? `${branchColor}11` : '#0c0c16');

  let html = `<div style="padding:10px 14px;background:${bgColor};border:1px solid ${borderColor};border-radius:3px;border-left:3px solid ${locked ? '#2a2a3a' : branchColor};">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
      <span style="color:${locked ? '#6a6a7a' : branchColor};font-size:12px;">${esc(name)}</span>
      ${passive ? '<span style="color:#6a6a7a;font-size:9px;background:#1a1a2a;padding:1px 5px;border-radius:2px;">PASSIVE</span>' : ''}
      ${locked ? '<span style="color:#6a6a7a;font-size:9px;">🔒</span>' : ''}
    </div>
    ${desc ? `<div style="color:#6a6a7a;font-size:10px;line-height:1.4;margin-bottom:6px;">${esc(desc)}</div>` : ''}
    <div style="display:flex;justify-content:space-between;align-items:center;">`;

  if (locked && available) {
    html += `<span style="color:#6a6a7a;font-size:10px;">Cost: ${cost} SP</span>`;
    html += `<button class="btn btn-small skill-unlock-btn" data-skill="${esc(skillId)}">UNLOCK</button>`;
  } else if (locked) {
    html += `<span style="color:#6a6a7a;font-size:10px;">Requires prerequisite</span>`;
    html += `<span></span>`;
  } else if (!passive) {
    html += `<span style="color:#4CAF50;font-size:10px;">✓ Unlocked</span>`;
    html += `<button class="btn btn-small skill-use-btn" data-skill="${esc(skillId)}">USE</button>`;
  } else {
    html += `<span style="color:#4CAF50;font-size:10px;">✓ Active (passive)</span>`;
    html += `<span></span>`;
  }

  html += `</div></div>`;
  return html;
}

/* ── Public API ── */
export function openSkills(layout) {
  render(layout);
}

export function closeSkills() {
  const ov = document.getElementById('skills-overlay');
  if (ov) ov.style.display = 'none';
}

export async function unlockSkill(skillId) {
  const slot = getState('gameSlot') || 'default';
  try {
    const d = await apiPost('/action', { command: `/unlock ${skillId}`, slot });
    if (d.narration && typeof window.appendNarration === 'function') window.appendNarration(d.narration);
    if (d.state) {
      setState('skill_points', d.state.skill_points);
      if (typeof window.updateState === 'function') window.updateState(d.state);
    }
    if (d.layout) {
      if (d.layout.skill_tree || d.layout.skills) render(d.layout);
      if (typeof window.updateLayout === 'function') window.updateLayout(d.layout);
    }
    toast(`Unlocked: ${skillId}`);
  } catch (e) {
    toast('Unlock failed: ' + e.message);
  }
}

export async function useSkill(skillId) {
  const slot = getState('gameSlot') || 'default';
  try {
    const d = await apiPost('/action', { command: `/skill ${skillId}`, slot });
    if (d.narration && typeof window.appendNarration === 'function') window.appendNarration(d.narration);
    if (d.layout) {
      if (d.layout.skill_tree || d.layout.skills) render(d.layout);
      if (typeof window.updateLayout === 'function') window.updateLayout(d.layout);
    }
    toast(`Used skill: ${skillId}`);
  } catch (e) {
    toast('Skill failed: ' + e.message);
  }
}
