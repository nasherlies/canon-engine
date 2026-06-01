/* ═══ Narrative Log ═══ */
import { $ } from './dom.js';

const MAX_MESSAGES = 500;
let logContent = null;
let scrollBtn = null;
let isNearBottom = true;

function getElements() {
  if (!logContent) {
    logContent = $('#log-content');
    scrollBtn = $('#btn-scroll-bottom');
  }
}

export function init() {
  getElements();
  const container = $('#narrative-log');
  if (!container) return;

  container.addEventListener('scroll', () => {
    const threshold = 80;
    isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
    if (scrollBtn) scrollBtn.hidden = isNearBottom;
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
    scrollBtn.hidden = false;
  }
}

export function clearLog() {
  getElements();
  if (logContent) logContent.innerHTML = '';
}

export function scrollToBottom() {
  getElements();
  const container = $('#narrative-log');
  if (container) {
    requestAnimationFrame(() => {
      container.scrollTop = container.scrollHeight;
    });
  }
  if (scrollBtn) scrollBtn.hidden = true;
  isNearBottom = true;
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
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
}
