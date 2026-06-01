/* ═══ Canon Engine — Main Entry Point ═══ */
/* Imports all 30 modules and wires the game UI */

// ── Core infrastructure ──
import * as store from './store.js';
import * as api from './api.js';
import * as dom from './dom.js';
import * as toastMod from './toast.js';
import * as modal from './modal.js';
import * as logMod from './log.js';
import * as sidebar from './sidebar.js';
import * as actionBar from './action_bar.js';
import * as session from './session.js';

// ── Feature modules ──
import * as combatHud from './combat_hud.js';
import * as travelMod from './travel.js';
import * as shopMod from './shop.js';
import * as craftingMod from './crafting.js';
import * as skillsMod from './skills.js';
import * as inventoryMod from './inventory.js';
import * as questMod from './quests.js';
import * as codexMod from './codex.js';
import * as factionsMod from './factions.js';
import * as npcsMod from './npcs.js';
import * as handbookMod from './handbook.js';
import * as commandPalette from './command_palette.js';

// ── Screen modules ──
import * as characterSelect from './character_select.js';
import * as createHero from './create_hero.js';
import * as chooseWorld from './choose_world.js';
import * as saveManager from './save_manager.js';
import * as settingsMod from './settings.js';
import * as pauseMod from './pause.js';
import * as tutorialMod from './tutorial.js';
import * as prefsMod from './prefs.js';

const { $, $$, show, hide } = dom;

// ── Screen Management ──
function showScreen(id) {
  // Hide boot/menu screens
  $$('.screen').forEach(s => s.classList.remove('show'));
  // Hide game
  const game = $('#game');
  if (game) game.style.display = 'none';

  if (id === 'boot' || id === 'menu') {
    const boot = $('#boot');
    if (boot) boot.classList.add('show');
  } else if (id === 'game') {
    if (game) game.style.display = 'flex';
    setTimeout(() => {
      const ci = $('#cinput');
      if (ci) ci.focus();
    }, 50);
  }
  store.set('activeScreen', id);
}

// ── Boot Sequence ──
async function boot() {
  showScreen('boot');
  const status = $('.boot-status');

  try {
    if (status) status.textContent = 'Connecting to server…';

    await api.health();

    if (status) status.textContent = 'Checking saves…';

    // Check for saves to show CONTINUE button
    let savesData = null;
    try { savesData = await api.saves(); } catch (e) { /* ok */ }

    if (status) status.textContent = 'Ready.';

    // Show menu
    goToMenu(savesData);
  } catch (err) {
    if (status) status.textContent = 'Failed to connect. Retrying…';
    setTimeout(boot, 3000);
  }
}

function goToMenu(savesData) {
  showScreen('boot');
  store.set('savesData', savesData);

  // Check if we need auth
  checkAuth(() => {
    // Auth passed — show menu buttons
    // The inline JS handles the menu UI, so we just ensure boot is visible
  });
}

async function checkAuth(onSuccess) {
  try {
    const result = await api.health();
    if (result && result.dev_mode === false) {
      // Need auth — show auth modal
      showAuthScreen(onSuccess);
    } else {
      onSuccess();
    }
  } catch (err) {
    onSuccess();
  }
}

function showAuthScreen(onSuccess) {
  modal.open('auth');
  const input = $('#auth-pw');
  const btn = $('#auth-submit');
  const errEl = $('#auth-err');

  if (input) input.value = '';
  if (errEl) errEl.style.display = 'none';

  const submit = async () => {
    const password = input ? input.value.trim() : '';
    if (!password) return;
    try {
      await api.action('/help', { slot: 'test' });
      modal.close('auth');
      if (onSuccess) onSuccess();
    } catch (err) {
      if (errEl) {
        errEl.textContent = 'Invalid passphrase';
        errEl.style.display = 'block';
      }
    }
  };

  if (btn) btn.onclick = submit;
  if (input) input.onkeydown = (e) => { if (e.key === 'Enter') submit(); };
  if (input) setTimeout(() => input.focus(), 100);
}

// ── Enter Game ──
function enterGame(data) {
  showScreen('game');
  logMod.init();
  if (data) session.handleResponse(data);
  actionBar.focus();
}

// Expose globals for modules that use window.cmd, window.enterGame, etc.
window.cmd = (text) => session.sendCommand(text);
window.enterGame = enterGame;
window.showScreen = showScreen;
window.appendNarration = (text) => logMod.appendMessage(text, 'narration');
window.updateLayout = (layout) => { store.set('layout', layout); session.applyLayout(layout); };
window.updateState = (state) => { if (state.player) store.set('player', state.player); };
window.openSettings = () => { import('./settings.js').then(m => m.openSettings()); };
window.doLoad = () => { import('./save_manager.js').then(m => m.openSaves()); };
window.doTutorial = () => { import('./tutorial.js').then(m => m.openTutorial()); };

// ── Main Init ──
// Use a flag to avoid double-initialization with inline JS
if (typeof window._modulesLoaded === 'undefined') {
  window._modulesLoaded = true;

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
}
