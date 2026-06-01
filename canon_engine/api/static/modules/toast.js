/* ═══ Toast Notifications ═══ */
const container = () => document.getElementById('toast-container');

const TYPE_ICONS = {
  info: 'ℹ',
  success: '✓',
  warning: '⚠',
  error: '✕',
  quest: '✦',
  lore: '📜',
  combat: '⚔',
};

export function show(message, type = 'info', duration = 3000) {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${TYPE_ICONS[type] || ''} ${escapeHtml(message)}</span>`;
  toast.style.setProperty('--toast-duration', `${duration}ms`);
  toast.querySelector('span') || toast;
  // Add countdown bar animation
  toast.style.cssText += `--toast-duration:${duration}ms`;
  const afterStyle = document.createElement('style');

  const el = container();
  if (!el) return;
  el.appendChild(toast);

  // Countdown bar via inline animation
  toast.style.setProperty('animation-duration', '0.3s');
  const bar = document.createElement('div');
  bar.style.cssText = `position:absolute;bottom:0;left:0;height:2px;background:var(--gold);width:100%;transition:width ${duration}ms linear;`;
  toast.appendChild(bar);
  requestAnimationFrame(() => { bar.style.width = '0%'; });

  const dismiss = () => {
    toast.classList.add('toast-dismiss');
    toast.addEventListener('animationend', () => toast.remove());
    setTimeout(() => toast.remove(), 300);
  };

  toast.addEventListener('click', dismiss);
  if (duration > 0) setTimeout(dismiss, duration);
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
