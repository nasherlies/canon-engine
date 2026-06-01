// ─── shop.js ─── Shop Overlay ───
import { apiPost } from './api.js';
import { getState, setState } from './store.js';
import { toast } from './toast.js';

/* ── Constants ── */
const RARITY_COLORS = {
  common: '#888', uncommon: '#4CAF50', rare: '#2196F3',
  epic: '#9C27B0', legendary: '#FFD700', mythical: '#f44336'
};

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function rarityColor(r) {
  return RARITY_COLORS[(r || '').toLowerCase()] || '#888';
}

let _layout = null;

/* ── Build overlay ── */
function ensureOverlay() {
  let ov = document.getElementById('shop-overlay');
  if (ov) return ov;
  ov = document.createElement('div');
  ov.id = 'shop-overlay';
  ov.style.cssText = `
    position:fixed;inset:0;z-index:800;display:none;
    background:rgba(0,0,0,0.92);overflow-y:auto;
    font-family:'Cascadia Mono','Fira Code',monospace;
    padding:20px;color:#c8c8d0;
  `;
  document.body.appendChild(ov);
  return ov;
}

/* ── Render ── */
function render(layout) {
  _layout = layout;
  const ov = ensureOverlay();
  const merchant = layout.merchant || {};
  const shopItems = layout.shop_items || layout.items || [];
  const playerItems = layout.player_items || getState('inventory') || [];
  const gold = layout.gold ?? getState('gold') ?? 0;

  let html = `<div style="max-width:900px;margin:0 auto;">`;

  // Header
  html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
    <div>
      <div style="color:#c8a84e;font-size:16px;letter-spacing:2px;">⬡ SHOP</div>
      <div style="color:#e8e8f0;font-size:13px;margin-top:4px;">${esc(erchant.name || 'Merchant')}</div>
      ${erchant.greeting ? `<div style="color:#6a6a7a;font-size:11px;font-style:italic;margin-top:2px;">"${esc(merchant.greeting)}"</div>` : ''}
    </div>
    <div style="text-align:right;">
      <div style="color:#c8a84e;font-size:14px;font-weight:bold;">${gold} Gold</div>
      <button class="btn btn-small" id="shop-close-btn" style="margin-top:6px;">CLOSE</button>
    </div>
  </div>`;

  // Shop items
  html += `<div style="margin-bottom:20px;">
    <div style="color:#8a7535;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Wares</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px;">`;

  shopItems.forEach(item => {
    const name = item.name || 'Item';
    const price = item.price ?? item.cost ?? 0;
    const rarity = (item.rarity || 'common').toLowerCase();
    const desc = item.description || item.lore || '';
    const canAfford = gold >= price;

    html += `<div style="padding:12px;background:#0c0c16;border:1px solid #2a2a3a;border-radius:3px;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${rarityColor(rarity)};"></span>
        <span style="color:${rarityColor(rarity)};font-size:13px;">${esc(name)}</span>
      </div>
      ${desc ? `<div style="color:#6a6a7a;font-size:11px;line-height:1.4;margin-bottom:6px;">${esc(desc)}</div>` : ''}
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="color:#c8a84e;font-size:12px;">${price} gold</span>
        <button class="btn btn-small shop-buy-btn" data-name="${esc(name)}" ${canAfford ? '' : 'disabled'}>BUY</button>
      </div>
    </div>`;
  });

  if (shopItems.length === 0) {
    html += `<div style="color:#6a6a7a;font-size:11px;padding:12px;">No wares available</div>`;
  }
  html += `</div></div>`;

  // Player items for selling
  html += `<div>
    <div style="color:#8a7535;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Your Items (to sell)</div>`;
  const pItems = Array.isArray(playerItems) ? playerItems : [];
  pItems.forEach(item => {
    const name = item.name || 'Item';
    const rarity = (item.rarity || 'common').toLowerCase();
    const basePrice = item.price || item.value || item.cost || 10;
    const sellPrice = Math.floor(basePrice * 0.5);
    const qty = item.quantity || item.qty || 1;
    html += `<div style="display:flex;align-items:center;gap:8px;padding:4px 8px;border-bottom:1px solid #1a1a2a;font-size:12px;">
      <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${rarityColor(rarity)};"></span>
      <span style="color:${rarityColor(rarity)};flex:1;">${esc(name)}</span>
      ${qty > 1 ? `<span style="color:#6a6a7a;font-size:10px;">×${qty}</span>` : ''}
      <span style="color:#6a6a7a;">${sellPrice}g</span>
      <button class="btn btn-small shop-sell-btn" data-name="${esc(name)}">SELL</button>
    </div>`;
  });
  if (pItems.length === 0) {
    html += `<div style="color:#6a6a7a;font-size:11px;padding:8px;">No items to sell</div>`;
  }
  html += `</div></div>`;

  ov.innerHTML = html;
  ov.style.display = 'flex';

  // Bind events
  ov.querySelectorAll('.shop-buy-btn').forEach(btn => {
    btn.addEventListener('click', () => buyItem(btn.dataset.name));
  });
  ov.querySelectorAll('.shop-sell-btn').forEach(btn => {
    btn.addEventListener('click', () => sellItem(btn.dataset.name));
  });
  const closeBtn = document.getElementById('shop-close-btn');
  if (closeBtn) closeBtn.addEventListener('click', closeShop);
}

/* ── Public API ── */
export function openShop(layout) {
  render(layout);
}

export function closeShop() {
  const ov = document.getElementById('shop-overlay');
  if (ov) ov.style.display = 'none';
}

export async function buyItem(name) {
  const slot = getState('gameSlot') || 'default';
  try {
    const d = await apiPost('/action', { command: `/buy ${name}`, slot });
    if (d.narration && typeof window.appendNarration === 'function') window.appendNarration(d.narration);
    if (d.state) {
      setState('gold', d.state.gold);
      if (typeof window.updateState === 'function') window.updateState(d.state);
    }
    if (d.layout) {
      if (d.layout.shop_present) render(d.layout);
      if (typeof window.updateLayout === 'function') window.updateLayout(d.layout);
    }
    toast(`Bought ${name}`);
  } catch (e) {
    toast('Buy failed: ' + e.message);
  }
}

export async function sellItem(name) {
  const slot = getState('gameSlot') || 'default';
  try {
    const d = await apiPost('/action', { command: `/sell ${name}`, slot });
    if (d.narration && typeof window.appendNarration === 'function') window.appendNarration(d.narration);
    if (d.state) {
      setState('gold', d.state.gold);
      if (typeof window.updateState === 'function') window.updateState(d.state);
    }
    if (d.layout) {
      if (d.layout.shop_present) render(d.layout);
      if (typeof window.updateLayout === 'function') window.updateLayout(d.layout);
    }
    toast(`Sold ${name}`);
  } catch (e) {
    toast('Sell failed: ' + e.message);
  }
}
