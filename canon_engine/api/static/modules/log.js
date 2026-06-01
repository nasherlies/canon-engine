/* ═══ Narrative Log ═══ */
import { $ } from './dom.js';

const MAX_MESSAGES = 500;
let logContent = null;
let scrollBtn = null;
let isNearBottom = true;

function getElements() {
  if (!logContent) {
    // Match actual HTML: #narr is the narrative container
    logContent = $('#narr');
    scrollBtn = $('#jump-bottom');
  }
}

export function init() {
  getElements();
  if (!logContent) return;

  logContent.addEventListener('scroll', () => {
    const threshold = 80;
    isNearBottom = logContent.scrollHeight - logContent.scrollTop - logContent.clientHeight < threshold;
    if (scrollBtn) scrollBtn.classList.toggle('show', !isNearBottom);
  });

  if (scrollBtn) {
    scrollBtn.addEventListener('click', () => {
      scrollToBottom();
    });
  }
}

export function appendMessage(text, type = 'narration') {
  getElements();
  if (!logContent) return;

  const msg = document.createElement('div');
  msg.className = `msg msg-${type}`;
  msg.innerHTML = formatText(text);
  logContent.appendChild(msg);

  // Prune old messages
  while (logContent.children.length > MAX_MESSAGES) {
    logContent.removeChild(logContent.firstChild);
  }

  if (isNearBottom) {
    scrollToBottom();
  } else if (scrollBtn) {
    scrollBtn.classList.add('show');
  }
}

export function clearLog() {
  getElements();
  if (logContent) logContent.innerHTML = '';
}

export function scrollToBottom() {
  getElements();
  if (logContent) {
    requestAnimationFrame(() => {
      logContent.scrollTop = logContent.scrollHeight;
    });
  }
  if (scrollBtn) scrollBtn.classList.remove('show');
  isNearBottom = true;
}

export function showLoading() {
  getElements();
  if (!logContent) return '';
  const id = 'ld-' + Date.now();
  const d = document.createElement('div');
  d.className = 'msg msg-sys';
  d.id = id;
  d.innerHTML = '<em>Thinking...</em>';
  logContent.appendChild(d);
  scrollToBottom();
  return id;
}

export function removeLoading(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatText(text) {
  if (!text) return '';
  // Basic markdown-like formatting
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="color:var(--gold);background:var(--panel);padding:0 3px">$1</code>')
    .replace(/\n/g, '<br>');
}
