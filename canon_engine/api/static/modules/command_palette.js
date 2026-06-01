// command_palette.js — Slash Command Autocomplete
// Canon Engine UI Module

let _dropdown = null;
let _visible = false;
let _selectedIndex = -1;
let _filteredCommands = [];
let _inputEl = null;

const COMMANDS = [
  // Combat
  { cmd: '/attack', desc: 'Strike the enemy', cat: 'Combat' },
  { cmd: '/block', desc: 'Defend yourself', cat: 'Combat' },
  { cmd: '/flee', desc: 'Run away from combat', cat: 'Combat' },
  { cmd: '/fight', desc: 'Start a combat encounter', cat: 'Combat' },
  { cmd: '/encounter', desc: 'Trigger a random encounter', cat: 'Combat' },
  { cmd: '/use', desc: 'Use an ability or item', cat: 'Combat' },
  { cmd: '/cast', desc: 'Cast a spell', cat: 'Combat' },

  // Social
  { cmd: '/say', desc: 'Speak dialogue', cat: 'Social' },
  { cmd: '/talk', desc: 'Talk to an NPC', cat: 'Social' },
  { cmd: '/gift', desc: 'Give item to an NPC', cat: 'Social' },
  { cmd: '/threaten', desc: 'Threaten an NPC', cat: 'Social' },
  { cmd: '/recruit', desc: 'Recruit an NPC', cat: 'Social' },
  { cmd: '/persuade', desc: 'Attempt persuasion', cat: 'Social' },
  { cmd: '/intimidate', desc: 'Intimidate target', cat: 'Social' },
  { cmd: '/trade', desc: 'Open trade with NPC', cat: 'Social' },

  // Exploration
  { cmd: '/look', desc: 'Examine surroundings', cat: 'Exploration' },
  { cmd: '/inv', desc: 'Check inventory', cat: 'Exploration' },
  { cmd: '/map', desc: 'View world map', cat: 'Exploration' },
  { cmd: '/go', desc: 'Move to a location', cat: 'Exploration' },
  { cmd: '/search', desc: 'Search the area', cat: 'Exploration' },
  { cmd: '/take', desc: 'Pick up an item', cat: 'Exploration' },
  { cmd: '/open', desc: 'Open a door or container', cat: 'Exploration' },
  { cmd: '/choices', desc: 'See branching options', cat: 'Exploration' },
  { cmd: '/collide', desc: 'Mix genres together', cat: 'Exploration' },
  { cmd: '/equip', desc: 'Equip a weapon or armor', cat: 'Exploration' },
  { cmd: '/drop', desc: 'Drop an item', cat: 'Exploration' },
  { cmd: '/craft', desc: 'Craft an item', cat: 'Exploration' },

  // Meta
  { cmd: '/help', desc: 'Show all commands', cat: 'Meta' },
  { cmd: '/stats', desc: 'View character stats', cat: 'Meta' },
  { cmd: '/companions', desc: 'View party members', cat: 'Meta' },
  { cmd: '/quests', desc: 'View quest log', cat: 'Meta' },
  { cmd: '/skills', desc: 'View abilities', cat: 'Meta' },
  { cmd: '/factions', desc: 'View faction standings', cat: 'Meta' },
  { cmd: '/save', desc: 'Save your game', cat: 'Meta' },
  { cmd: '/load', desc: 'Load a saved game', cat: 'Meta' },
  { cmd: '/summary', desc: 'Get session recap', cat: 'Meta' },
  { cmd: '/author', desc: 'Set story tone', cat: 'Meta' },
  { cmd: '/codex', desc: 'Open lore codex', cat: 'Meta' },
  { cmd: '/handbook', desc: 'Open player handbook', cat: 'Meta' },
  { cmd: '/tutorial', desc: 'Start tutorial', cat: 'Meta' },
  { cmd: '/godmode', desc: 'Enable god mode (debug)', cat: 'Meta' }
];

const CATEGORY_ORDER = ['Combat', 'Social', 'Exploration', 'Meta'];
const CATEGORY_COLORS = {
  Combat: '#cc3333',
  Social: '#6cb4c8',
  Exploration: '#33aa33',
  Meta: '#c8b16c'
};

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function fuzzyMatch(query, text) {
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  // Starts-with match
  if (t.startsWith(q)) return true;
  // Contains match
  if (t.includes(q)) return true;
  // Character-by-character fuzzy
  let qi = 0;
  for (let i = 0; i < t.length && qi < q.length; i++) {
    if (t[i] === q[qi]) qi++;
  }
  return qi === q.length;
}

function highlightMatch(text, query) {
  if (!query) return esc(text);
  const q = query.toLowerCase();
  const t = text;
  const tl = t.toLowerCase();
  const idx = tl.indexOf(q);
  if (idx >= 0) {
    return esc(t.substring(0, idx)) + '<b>' + esc(t.substring(idx, idx + q.length)) + '</b>' + esc(t.substring(idx + q.length));
  }
  // Fuzzy highlight
  let result = '';
  let qi = 0;
  for (let i = 0; i < t.length; i++) {
    if (qi < q.length && t[i].toLowerCase() === q[qi]) {
      result += '<b>' + esc(t[i]) + '</b>';
      qi++;
    } else {
      result += esc(t[i]);
    }
  }
  return result;
}

function createDropdown() {
  if (_dropdown) return _dropdown;
  const dropdown = document.createElement('div');
  dropdown.id = 'cmd-palette';
  dropdown.className = 'autocomplete';
  document.body.appendChild(dropdown);

  _dropdown = dropdown;
  return dropdown;
}

function filterCommands(query) {
  if (!query || query.length < 1) return [];
  // Strip leading /
  const q = query.startsWith('/') ? query.slice(1) : query;
  if (!q) return COMMANDS.slice(); // Show all if just /
  return COMMANDS.filter(c => fuzzyMatch(q, c.cmd.slice(1)));
}

function renderDropdown(filter) {
  if (!_dropdown) return;
  const matches = filterCommands(filter);
  _filteredCommands = matches;

  if (!matches.length) {
    _dropdown.classList.remove('show');
    _visible = false;
    return;
  }

  // Group by category
  const grouped = {};
  matches.forEach(m => {
    if (!grouped[m.cat]) grouped[m.cat] = [];
    grouped[m.cat].push(m);
  });

  let html = '';
  let flatIdx = 0;
  CATEGORY_ORDER.forEach(cat => {
    if (!grouped[cat]) return;
    const catColor = CATEGORY_COLORS[cat] || '#c8b16c';
    html += `<div class="ac-cat" style="color:${catColor};">${cat}</div>`;
    grouped[cat].forEach(m => {
      const selected = flatIdx === _selectedIndex ? ' selected' : '';
      const cmdHtml = highlightMatch(m.cmd, filter);
      html += `<div class="ac-item${selected}" data-cmd="${esc(m.cmd)}" data-idx="${flatIdx}">`;
      html += `<span class="ac-cmd">${cmdHtml}</span>`;
      html += `<span class="ac-desc">${esc(m.desc)}</span>`;
      html += `</div>`;
      flatIdx++;
    });
  });

  _dropdown.innerHTML = html;
  _dropdown.classList.add('show');
  _visible = true;

  // Click handlers
  _dropdown.querySelectorAll('.ac-item').forEach(item => {
    item.addEventListener('mousedown', (e) => {
      e.preventDefault();
      selectPaletteItem(item.dataset.cmd);
    });
  });
}

function scrollToSelected() {
  if (!_dropdown) return;
  const sel = _dropdown.querySelector('.ac-item.selected');
  if (sel) sel.scrollIntoView({ block: 'nearest' });
}

export function showPalette(filter) {
  createDropdown();
  if (!filter || !filter.startsWith('/')) {
    hidePalette();
    return;
  }
  _selectedIndex = -1;
  renderDropdown(filter);
}

export function hidePalette() {
  if (_dropdown) _dropdown.classList.remove('show');
  _visible = false;
  _selectedIndex = -1;
  _filteredCommands = [];
}

export function navigatePalette(direction) {
  if (!_visible || !_filteredCommands.length) return;
  const total = _filteredCommands.length;
  if (_selectedIndex < 0) {
    _selectedIndex = direction > 0 ? 0 : total - 1;
  } else {
    _selectedIndex += direction;
    if (_selectedIndex < 0) _selectedIndex = total - 1;
    if (_selectedIndex >= total) _selectedIndex = 0;
  }

  // Update visual selection
  if (_dropdown) {
    _dropdown.querySelectorAll('.ac-item').forEach((item, i) => {
      item.classList.toggle('selected', i === _selectedIndex);
    });
    scrollToSelected();
  }
}

export function selectPaletteItem(cmd) {
  const command = cmd || (_filteredCommands[_selectedIndex] ? _filteredCommands[_selectedIndex].cmd : null);
  if (!command) return;

  if (_inputEl) {
    _inputEl.value = command + ' ';
    _inputEl.focus();
  }
  hidePalette();
}

// Auto-attach to input field
function attachToInput() {
  _inputEl = document.getElementById('cinput');
  if (!_inputEl) return;

  _inputEl.addEventListener('input', () => {
    const v = _inputEl.value;
    if (v.startsWith('/')) showPalette(v);
    else hidePalette();
  });

  _inputEl.addEventListener('keydown', (e) => {
    if (!_visible) return;
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      navigatePalette(-1);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      navigatePalette(1);
    } else if (e.key === 'Enter' && _selectedIndex >= 0) {
      e.preventDefault();
      selectPaletteItem();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      hidePalette();
    } else if (e.key === 'Tab') {
      e.preventDefault();
      navigatePalette(1);
    }
  });

  _inputEl.addEventListener('blur', () => {
    setTimeout(hidePalette, 150);
  });
}

// Auto-initialize when DOM is ready
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachToInput);
  } else {
    attachToInput();
  }
}

export function getCommands() {
  return COMMANDS.slice();
}

export default { showPalette, hidePalette, navigatePalette, selectPaletteItem, getCommands };
