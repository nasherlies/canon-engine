// ─── travel.js ─── Travel Map Overlay ───
import { apiPost } from './api.js';
import { getState, setState } from './store.js';
import { toast } from './toast.js';

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

let _layout = null;

/* ── Overlay ── */
function ensureOverlay() {
  let ov = document.getElementById('travel-overlay');
  if (ov) return ov;
  ov = document.createElement('div');
  ov.id = 'travel-overlay';
  ov.style.cssText = `
    position:fixed;inset:0;z-index:800;display:none;
    background:rgba(0,0,0,0.92);overflow-y:auto;
    font-family:'Cascadia Mono','Fira Code',monospace;
    padding:20px;color:#c8c8d0;
  `;
  document.body.appendChild(ov);
  return ov;
}

/* ── Map node positions (deterministic layout) ── */
function layoutNodes(current, destinations) {
  const cx = 300, cy = 200;
  const radius = 140;
  const nodes = [];

  // Current location at center
  nodes.push({
    name: current || 'Unknown',
    x: cx, y: cy,
    current: true,
    distance: '0',
    time: '—'
  });

  // Destinations in a circle
  const n = destinations.length;
  destinations.forEach((dest, i) => {
    const angle = (2 * Math.PI * i / n) - Math.PI / 2;
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    nodes.push({
      name: dest.name || dest.location || dest.id || `Location ${i + 1}`,
      x, y,
      current: false,
      distance: dest.distance ?? '?',
      time: dest.time ?? dest.travel_time ?? '?',
      danger: dest.danger || dest.danger_level || ''
    });
  });

  return nodes;
}

/* ── Render ── */
function render(layout) {
  _layout = layout;
  const ov = ensureOverlay();
  const current = layout.current_location || layout.location || getState('gameState')?.location || 'Unknown';
  const destinations = layout.destinations || layout.travel_edges || layout.edges || [];

  const nodes = layoutNodes(current, destinations);
  const centerNode = nodes[0];
  const destNodes = nodes.slice(1);

  let html = `<div style="max-width:700px;margin:0 auto;">`;
  html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
    <div style="color:#c8a84e;font-size:16px;letter-spacing:2px;">🗺 TRAVEL MAP</div>
    <button class="btn btn-small" id="travel-close-btn">CLOSE</button>
  </div>`;

  // SVG map
  html += `<div style="background:#0c0c16;border:1px solid #2a2a3a;border-radius:4px;padding:10px;margin-bottom:16px;">`;
  html += `<svg viewBox="0 0 600 400" width="100%" height="400" style="display:block;">`;

  // Grid lines (subtle)
  for (let gx = 0; gx < 600; gx += 40) {
    html += `<line x1="${gx}" y1="0" x2="${gx}" y2="400" stroke="#1a1a2a" stroke-width="0.5"/>`;
  }
  for (let gy = 0; gy < 400; gy += 40) {
    html += `<line x1="0" y1="${gy}" x2="600" y2="${gy}" stroke="#1a1a2a" stroke-width="0.5"/>`;
  }

  // Edges (lines from center to destinations)
  destNodes.forEach(node => {
    html += `<line x1="${centerNode.x}" y1="${centerNode.y}" x2="${node.x}" y2="${node.y}" stroke="#2a2a3a" stroke-width="1" stroke-dasharray="4,4"/>`;
  });

  // Destination nodes
  destNodes.forEach((node, i) => {
    const dangerColor = node.danger === 'high' ? '#c44' : node.danger === 'medium' ? '#e09040' : '#4CAF50';
    html += `<g class="travel-node" data-dest="${esc(node.name)}" style="cursor:pointer;">`;
    html += `<circle cx="${node.x}" cy="${node.y}" r="24" fill="#12121e" stroke="#2a2a3a" stroke-width="1.5"/>`;
    html += `<circle cx="${node.x}" cy="${node.y}" r="4" fill="#6a6a7a"/>`;
    html += `<text x="${node.x}" y="${node.y + 36}" text-anchor="middle" fill="#c8c8d0" font-size="10" font-family="monospace">${esc(node.name.length > 16 ? node.name.slice(0, 14) + '..' : node.name)}</text>`;
    html += `<text x="${node.x}" y="${node.y + 48}" text-anchor="middle" fill="#6a6a7a" font-size="8" font-family="monospace">${esc(String(node.distance))} · ${esc(String(node.time))}</text>`;
    if (node.danger) {
      html += `<circle cx="${node.x + 18}" cy="${node.y - 18}" r="4" fill="${dangerColor}"/>`;
    }
    html += `</g>`;
  });

  // Center (current location)
  html += `<circle cx="${centerNode.x}" cy="${centerNode.y}" r="28" fill="rgba(200,168,78,0.15)" stroke="#c8a84e" stroke-width="2"/>`;
  html += `<circle cx="${centerNode.x}" cy="${centerNode.y}" r="6" fill="#c8a84e"/>`;
  html += `<text x="${centerNode.x}" y="${centerNode.y + 40}" text-anchor="middle" fill="#c8a84e" font-size="11" font-family="monospace" font-weight="bold">${esc(centerNode.name)}</text>`;
  html += `<text x="${centerNode.x}" y="${centerNode.y + 52}" text-anchor="middle" fill="#8a7535" font-size="9" font-family="monospace">YOU ARE HERE</text>`;

  html += `</svg></div>`;

  // Destination list (below map)
  html += `<div style="color:#8a7535;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Destinations</div>`;
  html += `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;">`;
  destNodes.forEach(node => {
    const dangerColor = node.danger === 'high' ? '#c44' : node.danger === 'medium' ? '#e09040' : '#4CAF50';
    html += `<div class="travel-dest-card" data-dest="${esc(node.name)}" style="padding:10px;background:#0c0c16;border:1px solid #2a2a3a;border-radius:3px;cursor:pointer;transition:border-color 0.2s;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="color:#e8e8f0;font-size:12px;">${esc(node.name)}</span>
        ${node.danger ? `<span style="color:${dangerColor};font-size:9px;">${esc(node.danger)}</span>` : ''}
      </div>
      <div style="color:#6a6a7a;font-size:10px;margin-top:4px;">${esc(String(node.distance))} · ${esc(String(node.time))}</div>
    </div>`;
  });
  html += `</div>`;

  html += `</div>`;
  ov.innerHTML = html;
  ov.style.display = 'flex';

  // Bind events
  ov.querySelectorAll('.travel-node, .travel-dest-card').forEach(el => {
    el.addEventListener('click', () => travelTo(el.dataset.dest));
    el.addEventListener('mouseenter', () => {
      if (el.classList.contains('travel-dest-card')) el.style.borderColor = '#c8a84e';
    });
    el.addEventListener('mouseleave', () => {
      if (el.classList.contains('travel-dest-card')) el.style.borderColor = '#2a2a3a';
    });
  });

  const closeBtn = document.getElementById('travel-close-btn');
  if (closeBtn) closeBtn.addEventListener('click', closeTravel);
}

/* ── Public API ── */
export function openTravel(layout) {
  render(layout);
}

export function closeTravel() {
  const ov = document.getElementById('travel-overlay');
  if (ov) ov.style.display = 'none';
}

export async function travelTo(destination) {
  if (!destination) return;
  const slot = getState('gameSlot') || 'default';
  try {
    toast(`Traveling to ${destination}...`);
    const d = await apiPost('/action', { command: `/travel ${destination}`, slot });
    if (d.narration && typeof window.appendNarration === 'function') window.appendNarration(d.narration);
    if (d.state) {
      setState('gameState', d.state);
      if (typeof window.updateState === 'function') window.updateState(d.state);
    }
    if (d.layout) {
      if (typeof window.updateLayout === 'function') window.updateLayout(d.layout);
    }
    closeTravel();
    toast(`Arrived at ${destination}`);
  } catch (e) {
    toast('Travel failed: ' + e.message);
  }
}
