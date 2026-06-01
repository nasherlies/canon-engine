/* ═══ Canon Engine — Main Entry Point ═══ */
import * as store from './store.js';
import * as api from './api.js';
import * as dom from './dom.js';
import * as toastMod from './toast.js';
import * as modal from './modal.js';
import * as logMod from './log.js';
import * as sidebar from './sidebar.js';
import * as actionBar from './action_bar.js';
import * as session from './session.js';

const { $, $$, show, hide } = dom;

// ── Screen Management ──
function showScreen(id) {
  $$('.screen').forEach(s => s.classList.remove('active'));
  const el = $(`#${id}`);
  if (el) el.classList.add('active');
  store.set('activeScreen', id);
}

// ── Boot Sequence ──
async function boot() {
  showScreen('boot');
  const fill = $('.boot-bar-fill');
  const status = $('.boot-status');

  try {
    if (status) status.textContent = 'Connecting to server…';
    if (fill) fill.style.width = '20%';

    await api.health();

    if (fill) fill.style.width = '60%';
    if (status) status.textContent = 'Loading presets…';

    // Optionally load presets
    let presets = null;
    try { presets = await api.presets(); } catch (e) { /* ok */ }

    if (fill) fill.style.width = '100%';
    if (status) status.textContent = 'Ready.';

    setTimeout(() => {
      // Check if auth is needed
      checkAuth(presets);
    }, 500);
  } catch (err) {
    if (status) status.textContent = 'Failed to connect. Retrying…';
    if (fill) fill.style.width = '0%';
    setTimeout(boot, 3000);
  }
}

async function checkAuth(presets) {
  try {
    const result = await api.health();
    // If health check passes without auth, go to menu
    goToMenu(presets);
  } catch (err) {
    // If 401/403, show auth screen
    if (err.message && (err.message.includes('401') || err.message.includes('403') || err.message.includes('password') || err.message.includes('auth'))) {
      showAuthScreen();
    } else {
      goToMenu(null);
    }
  }
}

function showAuthScreen() {
  showScreen('auth');
  const input = $('#auth-input');
  const btn = $('#auth-submit');
  const errEl = $('#auth-error');

  if (input) input.value = '';
  if (errEl) errEl.hidden = true;

  const submit = async () => {
    const password = input ? input.value.trim() : '';
    if (!password) return;
    try {
      await api.settingsKeys('POST', { password });
      goToMenu(null);
    } catch (err) {
      if (errEl) {
        errEl.textContent = 'Invalid passphrase';
        errEl.hidden = false;
      }
    }
  };

  if (btn) btn.onclick = submit;
  if (input) input.onkeydown = (e) => { if (e.key === 'Enter') submit(); };
  if (input) setTimeout(() => input.focus(), 100);
}

function goToMenu(presets) {
  showScreen('menu');
  store.set('presets', presets);
}

// ── Menu Wiring ──
function initMenu() {
  const newBtn = $('#menu-new');
  const loadBtn = $('#menu-load');
  const settingsBtn = $('#menu-settings');

  if (newBtn) newBtn.addEventListener('click', startNewGame);
  if (loadBtn) loadBtn.addEventListener('click', openSaves);
  if (settingsBtn) settingsBtn.addEventListener('click', () => modal.open('modal-settings'));
}

async function startNewGame() {
  showScreen('create-hero');
  const form = $('#hero-creator-form');
  if (!form) return;

  let presets = store.get('presets');
  if (!presets) {
    try { presets = await api.presets(); } catch (e) { presets = null; }
  }

  // Render character creation form
  const races = presets?.races || presets?.preset_races || ['Human', 'Elf', 'Dwarf', 'Halfling'];
  const classes = presets?.classes || presets?.preset_classes || ['Warrior', 'Mage', 'Rogue', 'Cleric'];

  form.innerHTML = `
    <div style="margin-bottom:12px;">
      <label style="display:block;color:var(--text-dim);font-size:0.85rem;margin-bottom:4px;">Name</label>
      <input type="text" id="hero-name" placeholder="Enter name" style="width:100%;" autocomplete="off">
    </div>
    <div style="margin-bottom:12px;">
      <label style="display:block;color:var(--text-dim);font-size:0.85rem;margin-bottom:4px;">Race</label>
      <select id="hero-race" style="width:100%;">
        ${races.map(r => `<option value="${typeof r === 'string' ? r : r.name}">${typeof r === 'string' ? r : r.name}</option>`).join('')}
      </select>
    </div>
    <div style="margin-bottom:12px;">
      <label style="display:block;color:var(--text-dim);font-size:0.85rem;margin-bottom:4px;">Class</label>
      <select id="hero-class" style="width:100%;">
        ${classes.map(c => `<option value="${typeof c === 'string' ? c : c.name}">${typeof c === 'string' ? c : c.name}</option>`).join('')}
      </select>
    </div>
    <div style="display:flex;gap:8px;margin-top:20px;">
      <button class="btn-gold" id="hero-create-btn" style="flex:1;">Create Hero</button>
      <button class="btn-menu" id="hero-back-btn" style="flex:0 0 auto;padding:8px 16px;">Back</button>
    </div>
  `;

  $('#hero-create-btn').onclick = async () => {
    const name = $('#hero-name').value.trim();
    const race = $('#hero-race').value;
    const cls = $('#hero-class').value;
    if (!name) { toastMod.show('Please enter a name', 'warning'); return; }

    // Try to start character
    const payload = { name, race, class: cls };
    try {
      showScreen('boot');
      $('.boot-status').textContent = 'Creating hero…';
      const result = await session.startCharacter(payload);
      if (result) {
        enterGame(result);
      } else {
        showScreen('create-hero');
      }
    } catch (err) {
      showScreen('create-hero');
    }
  };

  $('#hero-back-btn').onclick = () => goToMenu(null);
  setTimeout(() => { const n = $('#hero-name'); if (n) n.focus(); }, 100);
}

async function openSaves() {
  modal.open('modal-saves');
  const body = $('#saves-body');
  if (!body) return;
  body.innerHTML = '<p class="card-subtitle" style="text-align:center;">Loading saves…</p>';

  try {
    const data = await api.saves();
    const saves = data?.saves || data?.layout?.saves || [];

    if (saves.length === 0) {
      body.innerHTML = '<p class="card-subtitle" style="text-align:center;">No saved games found</p>';
      return;
    }

    body.innerHTML = saves.map(s => `
      <div class="stat-card" style="cursor:pointer;" data-slot="${s.slot || s.id || ''}">
        <div class="card-title">${s.name || s.title || `Save ${s.slot}`}</div>
        <div class="card-subtitle">${s.date || s.timestamp || ''} · Lv ${s.level || '?'}</div>
      </div>
    `).join('');

    body.querySelectorAll('[data-slot]').forEach(card => {
      card.addEventListener('click', async () => {
        modal.close('modal-saves');
        showScreen('boot');
        const status = $('.boot-status');
        if (status) status.textContent = 'Loading save…';
        const result = await session.loadSave(card.dataset.slot);
        if (result) enterGame(result);
        else showScreen('menu');
      });
    });
  } catch (err) {
    body.innerHTML = '<p class="card-subtitle" style="text-align:center;color:var(--danger);">Failed to load saves</p>';
  }
}

// ── Enter Game ──
function enterGame(data) {
  showScreen('game');
  logMod.init();
  if (data) session.handleResponse(data);
  actionBar.focus();
}

// ── Pause Menu ──
function initPauseMenu() {
  const pauseBtn = $('#btn-pause');
  if (pauseBtn) pauseBtn.addEventListener('click', () => modal.open('modal-pause'));

  const resumeBtn = $('#pause-resume');
  if (resumeBtn) resumeBtn.addEventListener('click', () => modal.close('modal-pause'));

  const saveBtn = $('#pause-save');
  if (saveBtn) saveBtn.addEventListener('click', async () => {
    modal.close('modal-pause');
    await session.sendCommand('/save');
    toastMod.show('Game saved', 'success');
  });

  const settingsBtn = $('#pause-settings');
  if (settingsBtn) settingsBtn.addEventListener('click', () => {
    modal.close('modal-pause');
    modal.open('modal-settings');
  });

  const quitBtn = $('#pause-quit');
  if (quitBtn) quitBtn.addEventListener('click', async () => {
    modal.close('modal-pause');
    await session.quitGame();
    goToMenu(null);
  });
}

// ── Settings ──
function initSettings() {
  const body = $('#settings-body');
  if (!body) return;

  store.loadSettings();
  store.applySettings();

  renderSettings(body);

  store.on('settings', () => {
    store.saveSettings();
    store.applySettings();
  });
}

function renderSettings(body) {
  const s = store.get('settings');
  body.innerHTML = `
    <div style="margin-bottom:16px;">
      <label style="display:block;color:var(--text-dim);font-size:0.85rem;margin-bottom:4px;">Theme</label>
      <select id="setting-theme" style="width:100%;">
        <option value="dark" ${s.theme === 'dark' ? 'selected' : ''}>Dark</option>
        <option value="ocean" ${s.theme === 'ocean' ? 'selected' : ''}>Ocean</option>
        <option value="forest" ${s.theme === 'forest' ? 'selected' : ''}>Forest</option>
        <option value="blood" ${s.theme === 'blood' ? 'selected' : ''}>Blood</option>
      </select>
    </div>
    <div style="margin-bottom:16px;">
      <label style="display:block;color:var(--text-dim);font-size:0.85rem;margin-bottom:4px;">Font Size: ${s.fontSize}x</label>
      <input type="range" id="setting-fontsize" min="0.8" max="1.4" step="0.05" value="${s.fontSize}" style="width:100%;">
    </div>
    <div style="margin-bottom:16px;">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
        <input type="checkbox" id="setting-crt" ${s.crtEffects ? 'checked' : ''}>
        <span style="color:var(--text-dim);font-size:0.85rem;">CRT Scanline Effects</span>
      </label>
    </div>
  `;

  const themeSelect = $('#setting-theme');
  const fontSlider = $('#setting-fontsize');
  const crtCheck = $('#setting-crt');

  if (themeSelect) themeSelect.onchange = () => {
    const settings = store.get('settings');
    settings.theme = themeSelect.value;
    store.set('settings', settings);
  };

  if (fontSlider) fontSlider.oninput = () => {
    const settings = store.get('settings');
    settings.fontSize = parseFloat(fontSlider.value);
    fontSlider.previousElementSibling.textContent = `Font Size: ${settings.fontSize}x`;
    store.set('settings', settings);
  };

  if (crtCheck) crtCheck.onchange = () => {
    const settings = store.get('settings');
    settings.crtEffects = crtCheck.checked;
    store.set('settings', settings);
  };
}

// ── Keyboard Shortcuts ──
function initKeyboard() {
  document.addEventListener('keydown', (e) => {
    // Only when in game screen
    if (store.get('activeScreen') !== 'game') return;
    // Don't override when typing in input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;

    // Number keys for sidebar tabs
    if (e.key >= '1' && e.key <= '5') {
      e.preventDefault();
      const tabs = ['stats', 'inventory', 'party', 'skills', 'quests'];
      sidebar.switchTab(tabs[parseInt(e.key) - 1]);
      return;
    }

    // Escape for pause
    if (e.key === 'Escape') {
      e.preventDefault();
      modal.open('modal-pause');
      return;
    }

    // Slash to focus input
    if (e.key === '/') {
      e.preventDefault();
      actionBar.focus();
    }
  });
}

// ── Main Init ──
document.addEventListener('DOMContentLoaded', () => {
  // Init subsystems
  modal.init();
  initMenu();
  initPauseMenu();
  initSettings();
  initKeyboard();
  sidebar.init();

  // Init action bar with send callback
  actionBar.init(async (text) => {
    await session.sendCommand(text);
  });

  // Start boot sequence
  boot();
});
