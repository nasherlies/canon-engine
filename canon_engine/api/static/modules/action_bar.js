/* ═══ Action Bar ═══ */
import { $, $$ } from './dom.js';
import * as store from './store.js';

let input = null;
let dropdown = null;
let historyArr = [];
let historyIdx = -1;
let sendCallback = null;
let acIndex = -1;

export function init(onSend) {
  input = $('#cinput');
  dropdown = $('#autocomplete');
  sendCallback = onSend;

  if (!input) return;

  // Mode buttons
  $$('.btn-mode').forEach(btn => {
    btn.addEventListener('click', () => {
      setMode(btn.dataset.mode);
    });
  });

  // Send button
  const sendBtn = $('#btn-send');
  if (sendBtn) sendBtn.addEventListener('click', handleSend);

  // Input events
  input.addEventListener('keydown', handleKeydown);
  input.addEventListener('input', handleInput);

  // Quick action buttons
  $$('.btn-quick').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.cmd && sendCallback) {
        sendCallback(btn.dataset.cmd);
      }
    });
  });
}

export function setMode(mode) {
  store.set('activeMode', mode);
  $$('.btn-mode').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
  if (input) {
    const placeholders = { do: 'What do you do?', say: 'What do you say?', think: 'What do you think?' };
    input.placeholder = placeholders[mode] || 'What do you do?';
    input.focus();
  }
}

export function getMode() {
  return store.get('activeMode') || 'do';
}

export function focus() {
  if (input) input.focus();
}

function handleSend() {
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;

  // Add to history
  if (historyArr[historyArr.length - 1] !== text) {
    historyArr.push(text);
    if (historyArr.length > 100) historyArr.shift();
  }
  historyIdx = -1;

  input.value = '';
  hideDropdown();

  if (sendCallback) {
    const mode = getMode();
    let cmd = text;
    if (mode === 'say' && !text.startsWith('/')) {
      cmd = `/say ${text}`;
    } else if (mode === 'think' && !text.startsWith('/')) {
      cmd = `/think ${text}`;
    }
    sendCallback(cmd);
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    // If autocomplete is open and has selection, use it
    if (dropdown && !dropdown.hidden && acIndex >= 0) {
      const items = dropdown.querySelectorAll('.autocomplete-item');
      if (items[acIndex]) {
        input.value = items[acIndex].dataset.value || items[acIndex].textContent;
        hideDropdown();
        return;
      }
    }
    handleSend();
    return;
  }

  if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (dropdown && !dropdown.hidden) {
      navigateDropdown(-1);
    } else if (historyArr.length > 0) {
      if (historyIdx === -1) historyIdx = historyArr.length;
      historyIdx = Math.max(0, historyIdx - 1);
      input.value = historyArr[historyIdx] || '';
    }
    return;
  }

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (dropdown && !dropdown.hidden) {
      navigateDropdown(1);
    } else if (historyIdx >= 0) {
      historyIdx = Math.min(historyArr.length, historyIdx + 1);
      input.value = historyArr[historyIdx] || '';
      if (historyIdx >= historyArr.length) historyIdx = -1;
    }
    return;
  }

  if (e.key === 'Escape') {
    hideDropdown();
    input.blur();
  }

  if (e.key === 'Tab' && dropdown && !dropdown.hidden) {
    e.preventDefault();
    const items = dropdown.querySelectorAll('.autocomplete-item');
    if (acIndex >= 0 && items[acIndex]) {
      input.value = items[acIndex].dataset.value || items[acIndex].textContent;
    }
    hideDropdown();
  }
}

function handleInput() {
  const val = input.value;
  if (val.startsWith('/')) {
    showSlashCommands(val);
  } else {
    hideDropdown();
  }
}

const SLASH_COMMANDS = [
  '/look', '/inventory', '/stats', '/map', '/party', '/quests',
  '/journal', '/codex', '/save', '/load', '/manual', '/help',
  '/equipment', '/skills', '/factions', '/travel', '/handbook',
  '/say', '/think', '/attack', '/use', '/equip', '/unequip',
  '/drop', '/examine', '/talk', '/rest', '/craft',
];

function showSlashCommands(val) {
  const matches = SLASH_COMMANDS.filter(c => c.startsWith(val.toLowerCase())).slice(0, 8);
  if (matches.length === 0 || (matches.length === 1 && matches[0] === val)) {
    hideDropdown();
    return;
  }
  if (!dropdown) return;

  dropdown.innerHTML = matches.map((cmd, i) =>
    `<div class="autocomplete-item${i === 0 ? ' selected' : ''}" data-value="${cmd}">${cmd}</div>`
  ).join('');
  dropdown.hidden = false;
  acIndex = 0;

  dropdown.querySelectorAll('.autocomplete-item').forEach((item, idx) => {
    item.addEventListener('click', () => {
      input.value = item.dataset.value;
      hideDropdown();
      input.focus();
    });
    item.addEventListener('mouseenter', () => {
      acIndex = idx;
      updateDropdownSelection();
    });
  });
}

function hideDropdown() {
  if (dropdown) dropdown.hidden = true;
  acIndex = -1;
}

function navigateDropdown(dir) {
  const items = dropdown ? dropdown.querySelectorAll('.autocomplete-item') : [];
  if (items.length === 0) return;
  acIndex = (acIndex + dir + items.length) % items.length;
  updateDropdownSelection();
}

function updateDropdownSelection() {
  if (!dropdown) return;
  dropdown.querySelectorAll('.autocomplete-item').forEach((item, i) => {
    item.classList.toggle('selected', i === acIndex);
  });
}
