// ─── create_hero.js ─── Hero Builder Screen ───
import { apiGet } from './api.js';
import { get as getState, set as setState } from './store.js';
import { show as toast } from './toast.js';

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

const TOTAL_POINTS = 60;
const STAT_NAMES = ['STR', 'DEX', 'INT', 'CHA', 'CON', 'LCK'];
const ARCHETYPE_SUGGESTIONS = ['Knight', 'Mage', 'Ranger', 'Rogue', 'Detective', 'Pirate', 'Paladin', 'Bard', 'Healer', 'Alchemist', 'Druid', 'Warlock', 'Scholar', 'Warrior'];
const RACE_SUGGESTIONS = ['Human', 'Elf', 'Dwarf', 'Orc', 'Robot', 'Vampire', 'Halfling', 'Tiefling', 'Dragonborn', 'Gnome', 'Half-Elf', 'Half-Orc'];
const SPEECH_STYLES = ['Casual', 'Formal', 'Archaic', 'Gruff', 'Eloquent', 'Terse', 'Poetic', 'Street slang', 'Scholarly', 'Sardonic'];
const GENRES = ['Medieval', 'Space', 'Gothic', 'Western', 'Anime', 'Cyberpunk', 'Post-apocalyptic', 'Noir', 'Steampunk', 'Horror'];

let _stats = { STR: 10, DEX: 10, INT: 10, CHA: 10, CON: 10, LCK: 10 };
let _selectedGenres = [];

/* ── Screen container ── */
function ensureScreen() {
  let el = document.getElementById('create-hero-mod');
  if (el) return el;
  el = document.createElement('div');
  el.id = 'create-hero-mod';
  el.className = 'screen creation-screen';
  document.body.appendChild(el);
  return el;
}

function sumStats() {
  return STAT_NAMES.reduce((s, k) => s + (_stats[k] || 0), 0);
}

function pointsLeft() {
  return TOTAL_POINTS - sumStats();
}

/* ── Render ── */
function render() {
  const el = ensureScreen();
  let html = `<div class="creation-card" style="max-width:600px;">
    <h2>◆ FORGE YOUR HERO ◆</h2>

    <div class="form-row">
      <div class="form-group">
        <label>Hero Name</label>
        <input type="text" id="ch-name" placeholder="Enter a name...">
      </div>
      <div class="form-group">
        <label>Race</label>
        <input type="text" id="ch-race" list="ch-race-list" placeholder="e.g. Human, Elf...">
        <datalist id="ch-race-list">${RACE_SUGGESTIONS.map(r => `<option value="${r}">`).join('')}</datalist>
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label>Archetype</label>
        <input type="text" id="ch-archetype" list="ch-arch-list" placeholder="e.g. Knight, Mage...">
        <datalist id="ch-arch-list">${ARCHETYPE_SUGGESTIONS.map(a => `<option value="${a}">`).join('')}</datalist>
      </div>
      <div class="form-group">
        <label>Speech Style</label>
        <select id="ch-speech">${SPEECH_STYLES.map(s => `<option value="${s.toLowerCase()}">${s}</option>`).join('')}</select>
      </div>
    </div>

    <div class="form-group">
      <label>Genre (up to 2)</label>
      <div class="genre-grid" id="ch-genre-grid">${GENRES.map(g => {
        const sel = _selectedGenres.includes(g.toLowerCase());
        return `<div class="genre-card${sel ? ' selected' : ''}" data-genre="${g.toLowerCase()}" style="cursor:pointer;">${g}</div>`;
      }).join('')}</div>
    </div>

    <div class="form-group">
      <label>Traits / Personality</label>
      <textarea id="ch-traits" rows="3" placeholder="Brave, curious, speaks in riddles..."></textarea>
    </div>

    <div class="form-group">
      <label>Attributes — <span class="points-left">Points remaining: <span id="ch-pts">${pointsLeft()}</span></span></label>
      <div id="ch-stats-area">${renderStatAlloc()}</div>
    </div>

    <div style="display:flex;gap:10px;margin-top:16px;">
      <button class="btn btn-small" id="ch-back-btn">◄ BACK</button>
      <button class="btn" id="ch-next-btn">CHOOSE WORLD ►</button>
    </div>
  </div>`;

  el.innerHTML = html;

  // Bind events
  document.querySelectorAll('#ch-genre-grid .genre-card').forEach(card => {
    card.addEventListener('click', () => {
      const g = card.dataset.genre;
      if (_selectedGenres.includes(g)) {
        _selectedGenres = _selectedGenres.filter(x => x !== g);
      } else if (_selectedGenres.length < 2) {
        _selectedGenres.push(g);
      } else {
        toast('Maximum 2 genres');
        return;
      }
      render();
    });
  });

  STAT_NAMES.forEach(k => {
    const minusBtn = document.querySelector(`[data-stat-minus="${k}"]`);
    const plusBtn = document.querySelector(`[data-stat-plus="${k}"]`);
    if (minusBtn) minusBtn.addEventListener('click', () => adjStat(k, -1));
    if (plusBtn) plusBtn.addEventListener('click', () => adjStat(k, 1));
  });

  const backBtn = document.getElementById('ch-back-btn');
  const nextBtn = document.getElementById('ch-next-btn');
  if (backBtn) backBtn.addEventListener('click', () => {
    import('./character_select.js').then(m => m.openCharacterSelect());
  });
  if (nextBtn) nextBtn.addEventListener('click', () => {
    const data = collectHeroData();
    if (!data.name) { toast('Enter a hero name'); return; }
    import('./choose_world.js').then(m => m.openChooseWorld(data));
  });
}

function renderStatAlloc() {
  return STAT_NAMES.map(k => {
    const val = _stats[k] || 0;
    const pct = Math.min(val / 20 * 100, 100);
    return `<div class="stat-alloc">
      <span class="s-name">${k}</span>
      <button class="btn btn-icon btn-small" data-stat-minus="${k}">−</button>
      <span class="s-val">${val}</span>
      <button class="btn btn-icon btn-small" data-stat-plus="${k}">+</button>
      <div class="s-bar"><div class="s-fill" style="width:${pct}%"></div></div>
    </div>`;
  }).join('');
}

function adjStat(name, delta) {
  const left = pointsLeft();
  if (delta > 0 && left <= 0) return;
  if (delta < 0 && (_stats[name] || 0) <= 1) return;
  _stats[name] = Math.max(1, Math.min(20, (_stats[name] || 0) + delta));
  render();
}

/* ── Public API ── */
export async function openCreateHero() {
  _stats = { STR: 10, DEX: 10, INT: 10, CHA: 10, CON: 10, LCK: 10 };
  _selectedGenres = [];

  // Load speech styles from server if available
  try {
    const d = await apiGet('/world_settings');
    if (d.speech_styles && d.speech_styles.length > 0) {
      // Will use server styles in render if available
      setState('speechStyles', d.speech_styles);
    }
  } catch (e) { /* fallback to defaults */ }

  const screen = ensureScreen();
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  render();
  screen.style.display = 'flex';
  void screen.offsetWidth;
  screen.classList.add('active');
}

export function collectHeroData() {
  const name = (document.getElementById('ch-name')?.value || '').trim();
  const archetype = (document.getElementById('ch-archetype')?.value || '').trim() || 'Warrior';
  const race = (document.getElementById('ch-race')?.value || '').trim() || 'Human';
  const speech = document.getElementById('ch-speech')?.value || 'casual';
  const traits = (document.getElementById('ch-traits')?.value || '').trim();

  return {
    name,
    archetype,
    race,
    speech_style: speech,
    genres: [..._selectedGenres],
    traits,
    stats: { ..._stats }
  };
}
