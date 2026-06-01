// ─── crafting.js ─── Crafting Panel ───
import { apiPost } from './api.js';
import { get as getState, set as setState } from './store.js';
import { show as toast } from './toast.js';

/* ── Constants ── */
const RARITY_COLORS = {
  common: '#888', uncommon: '#4CAF50', rare: '#2196F3',
  epic: '#9C27B0', legendary: '#FFD700', mythical: '#f44336'
};

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function rarityColor(r) {
  return RARITY_COLORS[(r || '').toLowerCase()] || '#888';
}

let _layout = null;

/* ── Overlay ── */
function ensureOverlay() {
  let ov = document.getElementById('crafting-overlay');
  if (ov) return ov;
  ov = document.createElement('div');
  ov.id = 'crafting-overlay';
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
  const recipes = layout.recipes || layout.crafting_recipes || [];
  const inventory = layout.player_items || getState('inventory') || [];

  // Build owned-materials lookup
  const owned = {};
  (Array.isArray(inventory) ? inventory : []).forEach(item => {
    const n = (item.name || '').toLowerCase();
    owned[n] = (owned[n] || 0) || (item.quantity || item.qty || 1);
  });

  let html = `<div style="max-width:800px;margin:0 auto;">`;
  html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
    <div style="color:#c8a84e;font-size:16px;letter-spacing:2px;">⚒ CRAFTING</div>
    <button class="btn btn-small" id="crafting-close-btn">CLOSE</button>
  </div>`;

  if (recipes.length === 0) {
    html += `<div style="color:#6a6a7a;font-size:12px;padding:20px;text-align:center;">No recipes available</div>`;
  }

  // Recipe cards
  html += `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;">`;
  recipes.forEach(recipe => {
    const result = recipe.result || recipe.output || {};
    const resultName = result.name || recipe.name || 'Result';
    const resultRarity = (result.rarity || recipe.rarity || 'common').toLowerCase();
    const materials = recipe.materials || recipe.ingredients || [];
    const dc = recipe.dc || recipe.difficulty;
    const check = recipe.check || recipe.ability || '';
    const recipeId = recipe.id || recipe.recipe_id || resultName;

    // Check if all materials owned
    let canCraft = true;
    const matHtml = materials.map(mat => {
      const matName = (mat.name || mat.item || '').toLowerCase();
      const needed = mat.quantity || mat.qty || mat.amount || 1;
      const have = owned[matName] || 0;
      const enough = have >= needed;
      if (!enough) canCraft = false;
      return `<div style="display:flex;align-items:center;gap:6px;font-size:11px;padding:1px 0;">
        <span style="color:${enough ? '#4CAF50' : '#c44'};">${enough ? '●' : '○'}</span>
        <span style="color:${enough ? '#c8c8d0' : '#6a6a7a'};">${esc(mat.name || mat.item || '?')}</span>
        <span style="color:${enough ? '#4CAF50' : '#c44'};">(${have} / ${needed})</span>
      </div>`;
    }).join('');

    html += `<div style="padding:14px;background:#0c0c16;border:1px solid #2a2a3a;border-radius:3px;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${rarityColor(resultRarity)};"></span>
        <span style="color:${rarityColor(resultRarity)};font-size:14px;">${esc(resultName)}</span>
      </div>
      <div style="color:#8a7535;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Materials</div>
      ${matHtml}
      ${dc ? `<div style="margin-top:8px;font-size:11px;color:#6a6a7a;">DC ${dc}${check ? ` — ${check.toUpperCase()} check` : ''}</div>` : ''}
      <div style="margin-top:10px;text-align:right;">
        <button class="btn btn-small craft-btn" data-recipe="${esc(recipeId)}" ${canCraft ? '' : 'disabled'}>CRAFT</button>
      </div>
    </div>`;
  });
  html += `</div></div>`;

  ov.innerHTML = html;
  ov.style.display = 'flex';

  // Bind events
  ov.querySelectorAll('.craft-btn').forEach(btn => {
    btn.addEventListener('click', () => craftItem(btn.dataset.recipe));
  });
  const closeBtn = document.getElementById('crafting-close-btn');
  if (closeBtn) closeBtn.addEventListener('click', closeCrafting);
}

/* ── Public API ── */
export function openCrafting(layout) {
  render(layout);
}

export function closeCrafting() {
  const ov = document.getElementById('crafting-overlay');
  if (ov) ov.style.display = 'none';
}

export async function craftItem(recipeId) {
  const slot = getState('gameSlot') || 'default';
  try {
    const d = await apiPost('/action', { command: `/craft ${recipeId}`, slot });
    if (d.narration && typeof window.appendNarration === 'function') window.appendNarration(d.narration);
    if (d.state && typeof window.updateState === 'function') window.updateState(d.state);
    if (d.layout) {
      if (d.layout.crafting_available) render(d.layout);
      if (typeof window.updateLayout === 'function') window.updateLayout(d.layout);
    }
    toast(`Crafted: ${recipeId}`);
  } catch (e) {
    toast('Craft failed: ' + e.message);
  }
}
