/* ═══ DOM Helpers ═══ */
export const $ = (sel, ctx = document) => ctx.querySelector(sel);
export const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

export function createElement(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'className') el.className = v;
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'innerHTML') el.innerHTML = v;
    else if (k === 'textContent') el.textContent = v;
    else el.setAttribute(k, v);
  }
  for (const child of [].concat(children)) {
    if (typeof child === 'string') el.appendChild(document.createTextNode(child));
    else if (child instanceof Node) el.appendChild(child);
  }
  return el;
}

export function show(el) { if (el) el.style.display = ''; }
export function hide(el) { if (el) el.style.display = 'none'; }
export function toggle(el) { if (el) el.style.display = el.style.display === 'none' ? '' : 'none'; }

export function addClass(el, cls) { if (el) el.classList.add(cls); }
export function removeClass(el, cls) { if (el) el.classList.remove(cls); }
export function toggleClass(el, cls) { if (el) el.classList.toggle(cls); }

export function html(el, content) { if (el) el.innerHTML = content; }
export function text(el, content) { if (el) el.textContent = content; }
