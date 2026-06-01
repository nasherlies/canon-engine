// pause.js — Pause Menu
// Canon Engine UI Module

import { show as showToast } from './toast.js';

let _modal = null;
let _isOpen = false;

function createModal() {
  if (_modal) return _modal;
  const modal = document.createElement('div');
  modal.id = 'pause-modal-ext';
  modal.className = 'modal';
  modal.style.zIndex = '120';
  modal.innerHTML = `
    <div class="modal-box" style="width:340px;">
      <h2>☰ MENU</h2>
      <div style="display:flex;flex-direction:column;gap:8px;margin-top:16px;">
        <button class="btn" id="pause-resume" style="width:100%;text-align:left;padding:12px 20px;font-size:15px;letter-spacing:1px;border-color:var(--gold);color:var(--gold);">
          ▶ RESUME
        </button>
        <button class="btn" id="pause-settings" style="width:100%;text-align:left;padding:12px 20px;font-size:15px;letter-spacing:1px;">
          ⚙ SETTINGS
        </button>
        <button class="btn" id="pause-load" style="width:100%;text-align:left;padding:12px 20px;font-size:15px;letter-spacing:1px;">
          💾 LOAD SAVE
        </button>
        <button class="btn" id="pause-save" style="width:100%;text-align:left;padding:12px 20px;font-size:15px;letter-spacing:1px;">
          💾 SAVE GAME
        </button>
        <button class="btn" id="pause-tutorial" style="width:100%;text-align:left;padding:12px 20px;font-size:15px;letter-spacing:1px;">
          📖 TUTORIAL
        </button>
        <button class="btn" id="pause-main" style="width:100%;text-align:left;padding:12px 20px;font-size:15px;letter-spacing:1px;border-color:#cc3333;color:#cc3333;">
          🏠 MAIN MENU
        </button>
      </div>
      <div style="margin-top:16px;text-align:center;color:#555;font-size:11px;">Press ESC to resume</div>
    </div>
  `;
  document.body.appendChild(modal);

  modal.querySelector('#pause-resume').addEventListener('click', resumeGame);
  modal.querySelector('#pause-settings').addEventListener('click', goToSettings);
  modal.querySelector('#pause-load').addEventListener('click', goToSaves);
  modal.querySelector('#pause-save').addEventListener('click', saveGame);
  modal.querySelector('#pause-tutorial').addEventListener('click', goToTutorial);
  modal.querySelector('#pause-main').addEventListener('click', goToMainMenu);

  modal.addEventListener('mousedown', (e) => {
    if (e.target === modal) resumeGame();
  });

  _modal = modal;
  return modal;
}

export function openPause() {
  createModal();
  _modal.classList.add('show');
  _isOpen = true;
}

export function closePause() {
  if (_modal) _modal.classList.remove('show');
  _isOpen = false;
}

export function resumeGame() {
  closePause();
}

export function goToSettings() {
  closePause();
  // Try to open settings via the settings module or inline function
  if (typeof window.openSettings === 'function') {
    window.openSettings();
  } else {
    // Try dynamic import
    import('./settings.js').then(m => m.openSettings()).catch(() => {
      if (typeof showToast === 'function') showToast('Settings not available', { color: '#cc3333' });
    });
  }
}

export function goToSaves() {
  closePause();
  if (typeof window.doLoad === 'function') {
    window.doLoad();
  } else {
    import('./save_manager.js').then(m => m.openSaves()).catch(() => {
      if (typeof showToast === 'function') showToast('Save manager not available', { color: '#cc3333' });
    });
  }
}

export function saveGame() {
  if (typeof window.cmd === 'function') {
    window.cmd('/save');
  }
  if (typeof showToast === 'function') {
    showToast('💾 Game saved', { color: '#c8b16c' });
  }
  closePause();
}

export function goToTutorial() {
  closePause();
  if (typeof window.doTutorial === 'function') {
    window.doTutorial();
  } else {
    import('./tutorial.js').then(m => m.openTutorial()).catch(() => {
      if (typeof showToast === 'function') showToast('Tutorial not available', { color: '#cc3333' });
    });
  }
}

export function goToMainMenu() {
  if (!confirm('Return to main menu? Unsaved progress will be auto-saved.')) return;
  // Auto-save first
  if (typeof window.cmd === 'function') {
    window.cmd('/save');
  }
  closePause();
  if (typeof window.showScreen === 'function') {
    window.showScreen('boot');
  }
  if (typeof showToast === 'function') {
    showToast('🏠 Returning to main menu...', { color: '#c8b16c' });
  }
}

export function isPaused() {
  return _isOpen;
}

// Keyboard handler: Escape toggles pause
function handleEscape(e) {
  if (e.key !== 'Escape') return;
  // Don't interfere if other modals are open
  const otherModals = ['settings-modal', 'saves-modal', 'setup', 'auth', 'quests-overlay', 'codex-overlay', 'npcs-overlay', 'factions-overlay', 'handbook-modal'];
  for (const id of otherModals) {
    const el = document.getElementById(id);
    if (el && el.classList.contains('show')) return;
  }
  // Only toggle if in game
  const game = document.getElementById('game');
  if (game && game.style.display === 'flex') {
    e.preventDefault();
    if (_isOpen) closePause();
    else openPause();
  }
}

// Auto-attach escape handler
if (typeof document !== 'undefined') {
  document.addEventListener('keydown', handleEscape);
}

export default { openPause, closePause, resumeGame, goToSettings, goToSaves, saveGame, goToTutorial, goToMainMenu, isPaused };
