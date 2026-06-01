// settings.js — Settings Modal
// Canon Engine UI Module

import { save, load, getAll, resetAll, getDefaults } from './prefs.js';
import { show as showToast } from './toast.js';

let _modal = null;

const DEFAULT_SETTINGS = {
  difficulty: 'normal',
  autosave: true,
  textSpeed: 3,
  theme: 'dark',
  fontSize: 16,
  crtEffects: false,
  highContrast: false,
  volMaster: 80,
  volMusic: 60,
  volSfx: 70,
  apiProvider: 'default',
  apiKey: '',
  apiModel: 'default'
};

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function maskKey(key) {
  if (!key || key.length < 8) return '••••••••';
  return key.substring(0, 4) + '••••' + key.substring(key.length - 4);
}

function createModal() {
  if (_modal) return _modal;
  const modal = document.createElement('div');
  modal.id = 'settings-modal-ext';
  modal.className = 'modal';
  modal.style.zIndex = '115';
  modal.innerHTML = `
    <div class="modal-box" style="width:520px;max-height:85dvh;">
      <button class="close-btn" id="settings-close">&times;</button>
      <h2>⚙ SETTINGS</h2>
      <div class="set-tabs" id="settings-tabs">
        <button class="set-tab active" data-tab="gameplay">GAMEPLAY</button>
        <button class="set-tab" data-tab="display">DISPLAY</button>
        <button class="set-tab" data-tab="audio">AUDIO</button>
        <button class="set-tab" data-tab="api">API</button>
      </div>

      <!-- Gameplay -->
      <div class="set-pane show" id="st-gameplay">
        <div class="set-section">DIFFICULTY</div>
        <div class="settings-row">
          <label>Difficulty</label>
          <select id="st-difficulty">
            <option value="easy">Easy</option>
            <option value="normal" selected>Normal</option>
            <option value="hard">Hard</option>
          </select>
        </div>
        <div class="set-section">AUTOMATION</div>
        <div class="settings-row">
          <label>Autosave</label>
          <button class="toggle-btn on" id="st-autosave">ON</button>
        </div>
        <div class="set-section">TEXT</div>
        <div class="settings-row">
          <label>Text Speed</label>
          <input type="range" id="st-textspeed" min="1" max="5" value="3">
          <span class="val-display" id="st-textspeed-val">3</span>
        </div>
      </div>

      <!-- Display -->
      <div class="set-pane" id="st-display">
        <div class="set-section">THEME</div>
        <div class="settings-row">
          <label>Theme</label>
          <div class="theme-swatch">
            <div class="theme-opt active" data-theme="dark"></div>
            <div class="theme-opt" data-theme="ocean"></div>
            <div class="theme-opt" data-theme="forest"></div>
            <div class="theme-opt" data-theme="blood"></div>
          </div>
        </div>
        <div class="set-section">TYPOGRAPHY</div>
        <div class="settings-row">
          <label>Font Size</label>
          <input type="range" id="st-fontsize" min="12" max="24" value="16">
          <span class="val-display" id="st-fontsize-val">16</span>
        </div>
        <div class="set-section">EFFECTS</div>
        <div class="settings-row">
          <label>CRT Effects</label>
          <button class="toggle-btn" id="st-crt">OFF</button>
        </div>
        <div class="settings-row">
          <label>High Contrast</label>
          <button class="toggle-btn" id="st-contrast">OFF</button>
        </div>
      </div>

      <!-- Audio -->
      <div class="set-pane" id="st-audio">
        <div class="set-section">VOLUME</div>
        <div class="settings-row">
          <label>Master</label>
          <input type="range" id="st-vol-master" min="0" max="100" value="80">
          <span class="val-display" id="st-vol-master-val">80</span>
        </div>
        <div class="settings-row">
          <label>Music</label>
          <input type="range" id="st-vol-music" min="0" max="100" value="60">
          <span class="val-display" id="st-vol-music-val">60</span>
        </div>
        <div class="settings-row">
          <label>SFX</label>
          <input type="range" id="st-vol-sfx" min="0" max="100" value="70">
          <span class="val-display" id="st-vol-sfx-val">70</span>
        </div>
      </div>

      <!-- API -->
      <div class="set-pane" id="st-api">
        <div class="set-section">CONNECTION</div>
        <div class="settings-row">
          <label>Provider</label>
          <select id="st-api-provider">
            <option value="default">Default (Server)</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="openrouter">OpenRouter</option>
            <option value="custom">Custom</option>
          </select>
        </div>
        <div class="settings-row">
          <label>API Key</label>
          <div style="flex:1;display:flex;gap:6px;">
            <span id="st-key-masked" style="flex:1;color:#666;font-size:13px;line-height:36px;">••••••••</span>
            <input type="password" id="st-apikey" placeholder="Enter key..." style="flex:1;">
          </div>
        </div>
        <div class="settings-row">
          <label>Model</label>
          <select id="st-api-model">
            <option value="default">Default</option>
            <option value="gpt-4o">GPT-4o</option>
            <option value="claude-3.5">Claude 3.5</option>
            <option value="llama-3">Llama 3</option>
            <option value="mixtral">Mixtral</option>
          </select>
        </div>
        <div class="settings-row">
          <label></label>
          <button class="btn" id="st-test-conn" style="flex:1;min-height:36px;font-size:13px;">TEST CONNECTION</button>
        </div>
        <div id="st-test-result" style="font-size:12px;padding:4px 0;color:#666;"></div>
      </div>

      <div class="set-footer">
        <button class="btn btn-danger" id="st-reset">RESET DEFAULTS</button>
        <div style="display:flex;gap:8px;">
          <button class="btn" id="st-cancel">CANCEL</button>
          <button class="btn" id="st-apply" style="border-color:var(--gold);color:var(--gold);">APPLY</button>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  // Tab switching
  modal.querySelectorAll('.set-tab').forEach(tab => {
    tab.addEventListener('click', () => switchSettingsTab(tab.dataset.tab));
  });

  // Toggle buttons
  modal.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.toggle('on');
      btn.textContent = btn.classList.contains('on') ? 'ON' : 'OFF';
    });
  });

  // Theme swatches
  modal.querySelectorAll('.theme-opt').forEach(opt => {
    opt.addEventListener('click', () => {
      modal.querySelectorAll('.theme-opt').forEach(o => o.classList.remove('active'));
      opt.classList.add('active');
      // Live preview
      const theme = opt.dataset.theme;
      document.body.className = document.body.className.replace(/theme-\w+/g, '');
      if (theme !== 'dark') document.body.classList.add('theme-' + theme);
    });
  });

  // Slider value displays
  ['st-textspeed', 'st-fontsize', 'st-vol-master', 'st-vol-music', 'st-vol-sfx'].forEach(id => {
    const slider = modal.querySelector(`#${id}`);
    const display = modal.querySelector(`#${id}-val`);
    if (slider && display) {
      slider.addEventListener('input', () => {
        display.textContent = slider.value;
      });
    }
  });

  // Buttons
  modal.querySelector('#st-reset').addEventListener('click', resetSettings);
  modal.querySelector('#st-cancel').addEventListener('click', closeSettings);
  modal.querySelector('#st-apply').addEventListener('click', applySettings);
  modal.querySelector('#st-test-conn').addEventListener('click', testConnection);

  // Close on backdrop
  modal.addEventListener('mousedown', (e) => {
    if (e.target === modal) closeSettings();
  });

  _modal = modal;
  return modal;
}

function loadSettingsToUI() {
  const s = getAll();
  const m = _modal;

  const diff = m.querySelector('#st-difficulty');
  if (diff) diff.value = s.difficulty || 'normal';

  const auto = m.querySelector('#st-autosave');
  if (auto) { auto.classList.toggle('on', !!s.autosave); auto.textContent = s.autosave ? 'ON' : 'OFF'; }

  const ts = m.querySelector('#st-textspeed');
  if (ts) { ts.value = s.textSpeed || 3; m.querySelector('#st-textspeed-val').textContent = s.textSpeed || 3; }

  const fs = m.querySelector('#st-fontsize');
  if (fs) { fs.value = s.fontSize || 16; m.querySelector('#st-fontsize-val').textContent = s.fontSize || 16; }

  const crt = m.querySelector('#st-crt');
  if (crt) { crt.classList.toggle('on', !!s.crtEffects); crt.textContent = s.crtEffects ? 'ON' : 'OFF'; }

  const hc = m.querySelector('#st-contrast');
  if (hc) { hc.classList.toggle('on', !!s.highContrast); hc.textContent = s.highContrast ? 'ON' : 'OFF'; }

  const vm = m.querySelector('#st-vol-master');
  if (vm) { vm.value = s.volMaster ?? 80; m.querySelector('#st-vol-master-val').textContent = s.volMaster ?? 80; }

  const vmu = m.querySelector('#st-vol-music');
  if (vmu) { vmu.value = s.volMusic ?? 60; m.querySelector('#st-vol-music-val').textContent = s.volMusic ?? 60; }

  const vs = m.querySelector('#st-vol-sfx');
  if (vs) { vs.value = s.volSfx ?? 70; m.querySelector('#st-vol-sfx-val').textContent = s.volSfx ?? 70; }

  const prov = m.querySelector('#st-api-provider');
  if (prov) prov.value = s.apiProvider || 'default';

  const masked = m.querySelector('#st-key-masked');
  if (masked) masked.textContent = s.apiKey ? maskKey(s.apiKey) : '••••••••';

  const apikey = m.querySelector('#st-apikey');
  if (apikey) apikey.value = '';

  const model = m.querySelector('#st-api-model');
  if (model) model.value = s.apiModel || 'default';

  // Theme swatch
  m.querySelectorAll('.theme-opt').forEach(opt => {
    opt.classList.toggle('active', opt.dataset.theme === (s.theme || 'dark'));
  });
}

function readUI() {
  const m = _modal;
  return {
    difficulty: m.querySelector('#st-difficulty')?.value || 'normal',
    autosave: m.querySelector('#st-autosave')?.classList.contains('on') ?? true,
    textSpeed: parseInt(m.querySelector('#st-textspeed')?.value) || 3,
    fontSize: parseInt(m.querySelector('#st-fontsize')?.value) || 16,
    crtEffects: m.querySelector('#st-crt')?.classList.contains('on') ?? false,
    highContrast: m.querySelector('#st-contrast')?.classList.contains('on') ?? false,
    volMaster: parseInt(m.querySelector('#st-vol-master')?.value) || 80,
    volMusic: parseInt(m.querySelector('#st-vol-music')?.value) || 60,
    volSfx: parseInt(m.querySelector('#st-vol-sfx')?.value) || 70,
    theme: _modal.querySelector('.theme-opt.active')?.dataset?.theme || 'dark',
    apiProvider: m.querySelector('#st-api-provider')?.value || 'default',
    apiKey: m.querySelector('#st-apikey')?.value || undefined,
    apiModel: m.querySelector('#st-api-model')?.value || 'default'
  };
}

export function switchSettingsTab(tabId) {
  if (!_modal) return;
  _modal.querySelectorAll('.set-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabId);
  });
  _modal.querySelectorAll('.set-pane').forEach(p => {
    p.classList.toggle('show', p.id === `st-${tabId}`);
  });
}

export function openSettings() {
  createModal();
  loadSettingsToUI();
  _modal.classList.add('show');
}

export function closeSettings() {
  if (_modal) _modal.classList.remove('show');
}

export function applySettings() {
  const settings = readUI();
  // Don't overwrite key if empty
  const newKey = _modal.querySelector('#st-apikey')?.value;
  if (!newKey) delete settings.apiKey;

  Object.entries(settings).forEach(([key, value]) => {
    if (value !== undefined) save(key, value);
  });

  // Apply theme
  document.body.className = document.body.className.replace(/theme-\w+/g, '');
  if (settings.theme !== 'dark') document.body.classList.add('theme-' + settings.theme);
  document.body.classList.toggle('high-contrast', !!settings.highContrast);
  document.documentElement.style.fontSize = settings.fontSize + 'px';

  closeSettings();
  if (typeof showToast === 'function') {
    showToast('⚙ Settings applied', { color: '#c8b16c' });
  }
}

export function resetSettings() {
  if (!confirm('Reset all settings to defaults?')) return;
  resetAll();
  loadSettingsToUI();
  if (typeof showToast === 'function') {
    showToast('⚙ Settings reset to defaults', { color: '#c8b16c' });
  }
}

function testConnection() {
  const result = _modal.querySelector('#st-test-result');
  if (!result) return;
  result.textContent = 'Testing...';
  result.style.color = '#666';

  const url = (typeof window !== 'undefined' && window.API) || window.location.origin;
  fetch(url + '/health')
    .then(r => r.json())
    .then(d => {
      result.textContent = 'Connected! Dev mode: ' + d.dev_mode;
      result.style.color = '#6c6';
    })
    .catch(e => {
      result.textContent = 'Connection failed: ' + e.message;
      result.style.color = '#c66';
    });
}

export default { openSettings, closeSettings, applySettings, resetSettings, switchSettingsTab };
