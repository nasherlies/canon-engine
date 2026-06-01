/* ═══ API Client ═══ */
import * as toast from './toast.js';

const BASE_URL = '';
const TIMEOUT = 240000; // 240s

async function request(method, endpoint, body = null) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT);

  try {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    };
    if (body !== null && method !== 'GET') {
      opts.body = JSON.stringify(body);
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, opts);
    clearTimeout(timer);

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errBody.detail || `HTTP ${res.status}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      toast.show('Request timed out', 'error');
      throw new Error('Request timed out');
    }
    toast.show(err.message || 'Network error', 'error');
    throw err;
  }
}

function post(endpoint, body = {}) {
  return request('POST', endpoint, body);
}

function get(endpoint) {
  return request('GET', endpoint);
}

// ── Generic API helpers (used by modules) ──

export function apiGet(endpoint) {
  return get(endpoint);
}

export function apiPost(endpoint, body = {}) {
  return post(endpoint, body);
}

// ── API Methods ──

export function health() {
  return get('/health');
}

export function presets() {
  return get('/presets');
}

export function worldSettings() {
  return get('/world_settings');
}

export function action(cmd, opts = {}) {
  return post('/action', { command: cmd, ...opts });
}

export function saves() {
  return post('/action', { command: '/saves' });
}

export function journal() {
  return post('/action', { command: '/journal' });
}

export function codex() {
  return post('/action', { command: '/codex' });
}

export function quests() {
  return post('/action', { command: '/quests' });
}

export function manual() {
  return post('/action', { command: '/manual' });
}

export function equipmentSlots() {
  return post('/action', { command: '/equipment' });
}

export function me() {
  return post('/action', { command: '/me' });
}

export function settingsKeys(method, data) {
  return post('/settings/keys', { method, ...data });
}

export function backstory(data) {
  return post('/backstory', data);
}

export function startCharacter(payload) {
  return post('/start_character', payload);
}

export function loadSave(slot) {
  return post('/action', { command: `/load ${slot}` });
}

export function quitGame() {
  return post('/action', { command: '/quit' });
}
