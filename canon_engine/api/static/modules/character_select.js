// ─── character_select.js ─── Character Select Screen ───
import { apiGet, apiPost } from './api.js';
import { get as getState, set as setState } from './store.js';
import { show as toast } from './toast.js';

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

let _presets = {};
let _selectedId = null;

/* ── Screen container ── */
function ensureScreen() {
  let el = document.getElementById('char-select-mod');
  if (el) return el;
  el = document.createElement('div');
  el.id = 'char-select-mod';
  el.className = 'screen creation-screen';
  el.innerHTML = `
    <div class="creation-card" style="max-width:700px;">
      <h2>◆ CHOOSE YOUR HERO ◆</h2>
      <div class="preset-grid" id="cs-preset-grid"></div>
      <div style="display:flex;gap:10px;margin-top:16px;">
        <button class="btn btn-small" id="cs-back-btn">◄ BACK</button>
        <button class="btn" id="cs-next-btn" disabled>NEXT ►</button>
      </div>
    </div>
  `;
  document.body.appendChild(el);
  return el;
}

/* ── Render grid ── */
function renderGrid() {
  const grid = document.getElementById('cs-preset-grid');
  if (!grid) return;
  let html = '';

  // Build Your Own tile
  html += `<div class="preset-card${_selectedId === '__custom' ? ' selected' : ''}" data-id="__custom" style="cursor:pointer;">
    <div style="font-size:28px;text-align:center;margin-bottom:6px;color:#c8a84e;">⚒</div>
    <div class="p-name" style="color:#c8a84e;text-align:center;">BUILD YOUR OWN</div>
    <div class="p-desc" style="text-align:center;">Forge a hero from scratch</div>
  </div>`;

  // Preset cards
  const keys = Object.keys(_presets);
  keys.forEach(id => {
    const p = _presets[id];
    const name = p.name || id;
    const arch = p.archetype || '';
    const genre = p.genre || p.setting || '';
    const desc = p.description || '';
    const letter = name.charAt(0).toUpperCase();
    const sel = _selectedId === id;

    html += `<div class="preset-card${sel ? ' selected' : ''}" data-id="${esc(id)}" style="cursor:pointer;">
      <div style="width:40px;height:40px;border:1px solid #2a2a3a;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;background:#12121e;">
        <span style="color:#c8a84e;font-size:18px;">${esc(letter)}</span>
      </div>
      <div class="p-name" style="text-align:center;">${esc(name)}</div>
      <div class="p-arch" style="text-align:center;">${esc(arch)}</div>
      ${genre ? `<div style="color:#6a6a7a;font-size:10px;text-align:center;margin-top:2px;">${esc(genre)}</div>` : ''}
      ${desc ? `<div class="p-desc" style="text-align:center;">${esc(desc)}</div>` : ''}
    </div>`;
  });

  grid.innerHTML = html;

  // Bind click events
  grid.querySelectorAll('.preset-card').forEach(card => {
    card.addEventListener('click', () => selectPreset(card.dataset.id));
  });
}

/* ── Select ── */
function selectPreset(id) {
  _selectedId = id;
  renderGrid();
  const nextBtn = document.getElementById('cs-next-btn');
  if (nextBtn) nextBtn.disabled = false;
}

/* ── Public API ── */
export async function openCharacterSelect() {
  const screen = ensureScreen();

  // Show screen
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  screen.style.display = 'flex';
  void screen.offsetWidth;
  screen.classList.add('active');

  // Load presets
  try {
    const d = await apiGet('/presets');
    _presets = d.presets || {};
    setState('presets', _presets);
  } catch (e) {
    toast('Failed to load presets: ' + e.message);
    _presets = getState('presets') || {};
  }

  _selectedId = null;
  renderGrid();

  // Bind buttons
  const backBtn = document.getElementById('cs-back-btn');
  const nextBtn = document.getElementById('cs-next-btn');
  if (backBtn) backBtn.onclick = () => {
    if (typeof window.showScreen === 'function') window.showScreen('boot-screen');
    else screen.classList.remove('active');
  };
  if (nextBtn) nextBtn.onclick = () => {
    if (!_selectedId) { toast('Select a hero'); return; }
    if (_selectedId === '__custom') {
      // Route to create-hero
      import('./create_hero.js').then(m => m.openCreateHero());
    } else {
      // Store preset and route to choose-world
      const preset = _presets[_selectedId];
      setState('selectedPreset', preset);
      setState('selectedPresetId', _selectedId);
      import('./choose_world.js').then(m => m.openChooseWorld(preset));
    }
  };
}

export function selectPresetById(id) {
  selectPreset(id);
}
