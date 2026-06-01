// ─── choose_world.js ─── World Picker Screen ───
import { apiGet, apiPost } from './api.js';
import { getState, setState } from './store.js';
import { toast } from './toast.js';

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

let _heroData = null;
let _worldSettings = [];
let _selectedGenre = null;
let _selectedCollision = '';
let _selectedLocation = null;
let _step = 1;

const GENRE_META = {
  medieval:     { label: 'Medieval',     icon: '⚔',  color: '#c8a84e' },
  space:        { label: 'Space',        icon: '🚀', color: '#2196F3' },
  gothic:       { label: 'Gothic',       icon: '🦇', color: '#9C27B0' },
  western:      { label: 'Western',      icon: '🤠', color: '#e09040' },
  anime:        { label: 'Anime',        icon: '🌸', color: '#f44336' },
  cyberpunk:    { label: 'Cyberpunk',    icon: '⚡', color: '#4CAF50' },
  postapoc:     { label: 'Post-Apoc',    icon: '☢',  color: '#c44' },
  noir:         { label: 'Noir',         icon: '🕵',  color: '#6a6a7a' },
  steampunk:    { label: 'Steampunk',    icon: '⚙',  color: '#e09040' },
  horror:       { label: 'Horror',       icon: '👁',  color: '#c44' },
};

const DEFAULT_LOCATIONS = {
  medieval:  ['Castle Courtyard', 'Dark Forest', 'Village Tavern', 'Ancient Ruins'],
  space:     ['Space Station', 'Alien Planet', 'Cargo Ship', 'Mining Colony'],
  gothic:    ['Haunted Manor', 'Foggy Graveyard', 'Cathedral', 'Witch Village'],
  western:   ['Dusty Saloon', 'Railroad Camp', 'Desert Canyon', 'Frontier Town'],
  anime:     ['Academy Gate', 'Spirit Forest', 'Neon City', 'Shrine'],
  cyberpunk: ['Megacorp Tower', 'Underground Lab', 'Neon Alley', 'Data Haven'],
  postapoc:  ['Bunker', 'Wasteland Outpost', 'Ruined City', 'Survivor Camp'],
  noir:      ['Rainy Office', 'Seedy Bar', 'Police Station', 'Docks'],
  steampunk: ['Clockwork Factory', 'Airship Port', 'Inventor Lab', 'Brass Market'],
  horror:    ['Abandoned Asylum', 'Fogbound Village', 'Crypt', 'Cursed Library'],
};

/* ── Screen ── */
function ensureScreen() {
  let el = document.getElementById('choose-world-mod');
  if (el) return el;
  el = document.createElement('div');
  el.id = 'choose-world-mod';
  el.className = 'screen creation-screen';
  document.body.appendChild(el);
  return el;
}

/* ── Render ── */
function render() {
  const el = ensureScreen();
  let html = `<div class="creation-card" style="max-width:700px;">
    <h2>◆ CHOOSE YOUR WORLD ◆</h2>`;

  // Step indicator
  html += `<div style="display:flex;gap:8px;margin-bottom:16px;">
    ${[1,2,3].map(s => `<div style="flex:1;height:3px;background:${s <= _step ? '#c8a84e' : '#2a2a3a'};border-radius:1px;transition:background 0.3s;"></div>`).join('')}
  </div>`;

  // Summary line
  const parts = [];
  if (_selectedGenre) parts.push(GENRE_META[_selectedGenre]?.label || _selectedGenre);
  if (_selectedCollision) parts.push(`+ ${_selectedCollision}`);
  if (_selectedLocation) parts.push(`→ ${_selectedLocation}`);
  if (parts.length > 0) {
    html += `<div style="color:#6a6a7a;font-size:11px;margin-bottom:12px;">${parts.join(' ')}</div>`;
  }

  // Step 1: Genre selection
  if (_step === 1) {
    html += `<div class="form-group"><label>Step 1: Genre / Setting</label>`;
    html += `<div class="genre-grid">`;
    const genres = _worldSettings.length > 0
      ? _worldSettings.map(w => w.id || w.genre)
      : Object.keys(GENRE_META);
    genres.forEach(g => {
      const meta = GENRE_META[g] || {};
      const sel = _selectedGenre === g;
      html += `<div class="genre-card${sel ? ' selected' : ''}" data-genre="${esc(g)}" style="cursor:pointer;min-width:120px;text-align:center;">
        <div style="font-size:24px;margin-bottom:4px;">${meta.icon || '✦'}</div>
        <div style="color:${sel ? '#c8a84e' : '#c8c8d0'};">${meta.label || esc(g)}</div>
      </div>`;
    });
    html += `</div></div>`;
  }

  // Step 2: Collision
  if (_step === 2) {
    html += `<div class="form-group"><label>Step 2: Collision Mode (optional secondary genre)</label>`;
    html += `<select id="cw-collision" style="width:100%;padding:6px 10px;background:#0a0a0f;border:1px solid #2a2a3a;color:#c8c8d0;">
      <option value="">None (single genre)</option>`;
    genres.forEach(g => {
      if (g !== _selectedGenre) {
        html += `<option value="${esc(g)}"${_selectedCollision === g ? ' selected' : ''}>${GENRE_META[g]?.label || esc(g)}</option>`;
      }
    });
    html += `</select></div>`;
  }

  // Step 3: Starting location
  if (_step === 3) {
    html += `<div class="form-group"><label>Step 3: Starting Location</label>`;
    html += `<div class="loc-grid">`;
    const locs = getLocations();
    locs.forEach(loc => {
      const sel = _selectedLocation === loc;
      html += `<div class="loc-card${sel ? ' selected' : ''}" data-loc="${esc(loc)}" style="cursor:pointer;">
        <div class="l-name">📍 ${esc(loc)}</div>
      </div>`;
    });
    // CUSTOM option
    html += `<div class="loc-card${_selectedLocation === '__custom' ? ' selected' : ''}" data-loc="__custom" style="cursor:pointer;border-style:dashed;">
      <div class="l-name" style="color:#c8a84e;">✏ CUSTOM</div>
      <div class="l-blurb">Describe your own starting location</div>
    </div>`;
    html += `</div></div>`;

    if (_selectedLocation === '__custom') {
      html += `<div class="form-group">
        <label>Custom Location</label>
        <input type="text" id="cw-custom-loc" placeholder="Describe your starting location..." style="width:100%;padding:6px 10px;background:#0a0a0f;border:1px solid #2a2a3a;color:#c8c8d0;">
      </div>`;
    }
  }

  // Buttons
  html += `<div style="display:flex;gap:10px;margin-top:16px;">`;
  html += `<button class="btn btn-small" id="cw-back-btn">◄ BACK</button>`;
  if (_step < 3) {
    html += `<button class="btn" id="cw-next-btn">NEXT ►</button>`;
  } else {
    html += `<button class="btn" id="cw-start-btn" ${_selectedLocation ? '' : 'disabled'}>START ADVENTURE ►</button>`;
  }
  html += `</div></div>`;

  el.innerHTML = html;

  // Bind events
  el.querySelectorAll('[data-genre]').forEach(card => {
    card.addEventListener('click', () => {
      _selectedGenre = card.dataset.genre;
      _step = 2;
      render();
    });
  });

  const collSel = document.getElementById('cw-collision');
  if (collSel) collSel.addEventListener('change', () => { _selectedCollision = collSel.value; });

  el.querySelectorAll('[data-loc]').forEach(card => {
    card.addEventListener('click', () => {
      _selectedLocation = card.dataset.loc;
      render();
    });
  });

  const backBtn = document.getElementById('cw-back-btn');
  if (backBtn) backBtn.addEventListener('click', () => {
    if (_step > 1) { _step--; render(); }
    else import('./create_hero.js').then(m => m.openCreateHero());
  });

  const nextBtn = document.getElementById('cw-next-btn');
  if (nextBtn) nextBtn.addEventListener('click', () => {
    if (_step === 1 && !_selectedGenre) { toast('Select a genre'); return; }
    _step++;
    render();
  });

  const startBtn = document.getElementById('cw-start-btn');
  if (startBtn) startBtn.addEventListener('click', startAdventure);
}

function getLocations() {
  // Try server data first
  const setting = _worldSettings.find(w => (w.id || w.genre) === _selectedGenre);
  if (setting && setting.locations && setting.locations.length > 0) {
    return setting.locations.map(l => l.label || l.id || l.name || l);
  }
  // Fallback defaults
  return DEFAULT_LOCATIONS[_selectedGenre] || ['Starting Area', 'Town Center', 'Wilderness', 'Safe Haven'];
}

/* ── Public API ── */
export async function openChooseWorld(heroData) {
  _heroData = heroData || getState('selectedPreset') || {};
  _selectedGenre = null;
  _selectedCollision = '';
  _selectedLocation = null;
  _step = 1;

  // Load world settings
  try {
    const d = await apiGet('/world_settings');
    _worldSettings = d.settings || [];
    setState('worldSettings', _worldSettings);
    if (d.speech_styles) setState('speechStyles', d.speech_styles);
  } catch (e) {
    _worldSettings = getState('worldSettings') || [];
  }

  const screen = ensureScreen();
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  render();
  screen.style.display = 'flex';
  void screen.offsetWidth;
  screen.classList.add('active');
}

export async function startAdventure() {
  if (!_selectedGenre || !_selectedLocation) {
    toast('Select a genre and location');
    return;
  }

  const hero = _heroData || {};
  let location = _selectedLocation;
  if (location === '__custom') {
    location = (document.getElementById('cw-custom-loc')?.value || '').trim();
    if (!location) { toast('Enter a custom location'); return; }
  }

  const payload = {
    name: hero.name || 'Adventurer',
    archetype: hero.archetype || 'Warrior',
    race: hero.race || 'Human',
    stats: hero.stats || { STR: 10, DEX: 10, INT: 10, CHA: 10, CON: 10, LCK: 10 },
    speech_style: hero.speech_style || 'casual',
    traits: hero.traits || '',
    setting_primary: _selectedGenre,
    setting_secondary: _selectedCollision || '',
    starting_location: location
  };

  try {
    toast('Starting adventure...');
    const d = await apiPost('/start_character', payload);
    setState('gameSlot', 'default');
    setState('gameState', d.state || {});
    // Navigate to game
    if (typeof window.enterGame === 'function') {
      window.enterGame(d);
    } else if (typeof window.showScreen === 'function') {
      window.showScreen('game-hud');
    }
    // Trigger layout/state updates
    if (d.narration && typeof window.appendNarration === 'function') window.appendNarration(d.narration);
    if (d.layout && typeof window.updateLayout === 'function') window.updateLayout(d.layout);
    if (d.state && typeof window.updateState === 'function') window.updateState(d.state);
  } catch (e) {
    toast('Failed to start: ' + e.message);
  }
}
