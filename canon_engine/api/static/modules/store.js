/* ═══ State Management ═══ */

const listeners = {};
let state = {
  activeScreen: 'boot',
  activeSidebarTab: 'stats',
  activeMode: 'do',
  player: null,
  layout: null,
  combat: null,
  quests: [],
  codex: {},
  settings: {
    theme: 'dark',
    fontSize: 1,
    crtEffects: false,
  },
};

export function get(key) {
  return key ? state[key] : state;
}

export function set(key, value) {
  const old = state[key];
  state[key] = value;
  emit(key, value, old);
}

export function update(partial) {
  for (const [k, v] of Object.entries(partial)) {
    set(k, v);
  }
}

// EventBus
export function on(event, fn) {
  if (!listeners[event]) listeners[event] = [];
  listeners[event].push(fn);
  return () => off(event, fn);
}

export function off(event, fn) {
  if (!listeners[event]) return;
  listeners[event] = listeners[event].filter(f => f !== fn);
}

export function emit(event, ...args) {
  if (listeners[event]) listeners[event].forEach(fn => fn(...args));
  if (listeners['*']) listeners['*'].forEach(fn => fn(event, ...args));
}

// Settings persistence
const SETTINGS_KEY = 'canon-engine-settings';

// ── Aliases used by modules ──
export function getState(key) { return get(key); }
export function setState(key, value) { set(key, value); }

export function loadSettings() {
  try {
    const saved = localStorage.getItem(SETTINGS_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      state.settings = { ...state.settings, ...parsed };
    }
  } catch (e) { /* ignore */ }
  return state.settings;
}

export function saveSettings() {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(state.settings));
  } catch (e) { /* ignore */ }
}

export function applySettings() {
  const s = state.settings;
  document.documentElement.setAttribute('data-theme', s.theme);
  document.documentElement.style.setProperty('--font-scale', s.fontSize);
  document.body.classList.toggle('crt-enabled', s.crtEffects);
}
