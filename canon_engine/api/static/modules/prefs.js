// prefs.js — Preferences persistence via localStorage
// Canon Engine UI Module

const STORAGE_KEY = 'canon_preferences';

const DEFAULTS = {
  theme: 'dark',
  fontSize: 16,
  crtEffects: false,
  highContrast: false,
  volMaster: 80,
  volMusic: 60,
  volSfx: 70,
  apiKey: '',
  apiModel: 'default',
  difficulty: 'normal',
  autosave: true,
  textSpeed: 3,
  fontfamily: 'mono',
  uiscale: 100,
  layout: 'standard',
  tutorialHints: true
};

let _cache = null;

function _loadAll() {
  if (_cache) return _cache;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    _cache = raw ? { ...DEFAULTS, ...JSON.parse(raw) } : { ...DEFAULTS };
  } catch (e) {
    _cache = { ...DEFAULTS };
  }
  return _cache;
}

function _saveAll(prefs) {
  _cache = prefs;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch (e) {
    console.warn('[prefs] Failed to save to localStorage:', e);
  }
}

export function save(key, value) {
  const prefs = _loadAll();
  prefs[key] = value;
  _saveAll(prefs);
}

export function load(key, defaultValue) {
  const prefs = _loadAll();
  if (key in prefs) return prefs[key];
  if (defaultValue !== undefined) return defaultValue;
  return key in DEFAULTS ? DEFAULTS[key] : null;
}

export function getAll() {
  return { ..._loadAll() };
}

export function setAll(obj) {
  const prefs = _loadAll();
  Object.assign(prefs, obj);
  _saveAll(prefs);
}

export function resetAll() {
  _saveAll({ ...DEFAULTS });
}

export function getDefaults() {
  return { ...DEFAULTS };
}

export default { save, load, getAll, setAll, resetAll, getDefaults };
