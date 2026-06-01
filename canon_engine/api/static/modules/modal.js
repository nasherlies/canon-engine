/* ═══ Modal System ═══ */
import { $, addClass, removeClass } from './dom.js';

const openStack = [];

export function open(id) {
  const el = $(`#${id}`);
  if (!el) return;
  // Close any existing modal first
  if (openStack.length) {
    const top = openStack[openStack.length - 1];
    if (top !== id) close(top);
  }
  addClass(el, 'show');
  if (!openStack.includes(id)) openStack.push(id);
  document.body.style.overflow = 'hidden';
}

export function close(id) {
  const el = $(`#${id}`);
  if (!el) return;
  removeClass(el, 'show');
  const idx = openStack.indexOf(id);
  if (idx !== -1) openStack.splice(idx, 1);
  if (openStack.length === 0) document.body.style.overflow = '';
}

export function toggle(id) {
  const el = $(`#${id}`);
  if (!el) return;
  if (el.classList.contains('show')) close(id);
  else open(id);
}

export function closeAll() {
  while (openStack.length) close(openStack[openStack.length - 1]);
}

export function isOpen(id) {
  return openStack.includes(id);
}

export function init() {
  // Close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && openStack.length) {
      e.preventDefault();
      close(openStack[openStack.length - 1]);
    }
  });

  // Close on backdrop click
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal') && e.target.classList.contains('show')) {
      close(e.target.id);
    }
  });

  // Close buttons
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-close]');
    if (btn) {
      close(btn.dataset.close);
    }
  });
}
