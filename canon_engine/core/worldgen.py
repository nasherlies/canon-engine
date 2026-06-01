"""Canon Engine — Seeded procedural world generation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from collections import deque

# ── Content loader ────────────────────────────────────────────────────────

_CONTENT_DIR = Path(os.environ.get(
    "CANON_CONTENT_DIR",
    Path(__file__).resolve().parents[2] / "content",
))


def _load_json(name: str) -> dict:
    p = _CONTENT_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


# ── Seeded RNG helper ─────────────────────────────────────────────────────

class SeededRNG:
    """Deterministic RNG from a seed string."""

    def __init__(self, seed: str | int):
        if isinstance(seed, int):
            seed = str(seed)
        h = hashlib.sha256(seed.encode()).hexdigest()
        self._state = int(h[:16], 16)

    def next_int(self, lo: int, hi: int) -> int:
        """Return random int in [lo, hi]."""
        self._state = (self._state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        if hi <= lo:
            return lo
        return lo + (self._state % (hi - lo + 1))

    def next_float(self) -> float:
        self._state = (self._state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        return self._state / 0xFFFFFFFFFFFFFFFF

    def pick(self, items: list) -> Any:
        if not items:
            return None
        return items[self.next_int(0, len(items) - 1)]

    def weighted_pick(self, items: list[dict], weight_key: str = "weight") -> dict | None:
        """Pick item proportional to weight_key."""
        if not items:
            return None
        total = sum(item.get(weight_key, 1) for item in items)
        r = self.next_float() * total
        cumulative = 0.0
        for item in items:
            cumulative += item.get(weight_key, 1)
            if r <= cumulative:
                return item
        return items[-1]


# ── World generation ──────────────────────────────────────────────────────

def generate_world(seed: str | int, setting_primary: str = "medieval_fantasy") -> dict:
    """Deterministic world from seed. Returns a world graph dict."""
    rng = SeededRNG(seed)
    tables = _load_json("worldgen_tables.json")

    # Generate nodes (8-15 locations)
    num_nodes = rng.next_int(8, 15)
    biomes_data = tables.get("biomes", {})
    biome_list = []
    for bname, bdata in biomes_data.items():
        biome_list.append({"id": bname, **bdata})

    name_frags = tables.get("place_name_fragments", {})
    prefixes = name_frags.get("prefix", ["Unknown"])
    suffixes = name_frags.get("suffix", ["place"])
    separators = name_frags.get("separator", [""])

    nodes = []
    used_names = set()
    for i in range(num_nodes):
        biome = rng.weighted_pick(biome_list) or biome_list[0]
        # Generate unique name
        name = f"{rng.pick(prefixes)}{rng.pick(separators)}{rng.pick(suffixes)}"
        for _ in range(50):
            p = rng.pick(prefixes)
            s = rng.pick(suffixes)
            sep = rng.pick(separators)
            name = f"{p}{sep}{s}"
            if name not in used_names:
                used_names.add(name)
                break
        feature = rng.pick(biome.get("features", ["clearing"]))
        node = {
            "id": f"node_{i}",
            "name": name,
            "biome": biome["id"],
            "feature": feature,
            "faction_influence": {},
            "lore_revealed": False,
            "visited": False,
        }
        nodes.append(node)

    # Generate edges (ensure connected graph)
    edges = []
    for i in range(1, num_nodes):
        # Connect to a random previous node (minimum spanning tree)
        target = rng.next_int(0, i - 1)
        edges.append({"from": nodes[i]["id"], "to": nodes[target]["id"]})
    # Add 1-4 extra edges for loops
    extras = rng.next_int(1, min(4, num_nodes - 1))
    for _ in range(extras):
        a = rng.next_int(0, num_nodes - 1)
        b = rng.next_int(0, num_nodes - 1)
        if a != b:
            edge = {"from": nodes[a]["id"], "to": nodes[b]["id"]}
            # Avoid duplicates
            if not any(e["from"] == edge["from"] and e["to"] == edge["to"] for e in edges):
                edges.append(edge)

    # Generate lore fragments per node
    lore_templates = tables.get("lore_templates", [
        "Ancient ruins speak of a forgotten civilization.",
        "Strange lights are seen here on moonless nights.",
    ])
    events = tables.get("lore_events", ["war"])
    creatures = tables.get("lore_creatures", ["beast"])
    artifacts = tables.get("lore_artifacts", ["relic"])
    dungeon_types = tables.get("lore_dungeon_types", ["cavern"])

    for node in nodes:
        template = rng.pick(lore_templates)
        node["lore"] = template.format(
            prefix=node["name"],
            event=rng.pick(events),
            creature=rng.pick(creatures),
            artifact=rng.pick(artifacts),
            feature=node["feature"],
            dungeon_type=rng.pick(dungeon_types),
            faction_a="the old kingdom",
            faction_b="the invaders",
        )

    # Assign faction influences
    factions_content = _load_json("factions.json")
    faction_ids = [k for k in factions_content.keys() if k != "_meta"]
    for node in nodes:
        # Each node may have 0-2 faction influences
        num_inf = rng.next_int(0, 2)
        for _ in range(num_inf):
            fid = rng.pick(faction_ids) if faction_ids else "unknown"
            strength = rng.next_int(1, 5)
            node["faction_influence"][fid] = strength

    return {
        "seed": str(seed),
        "setting": setting_primary,
        "nodes": nodes,
        "edges": edges,
    }


def map_to_travel_edges(map_graph: dict) -> list[dict]:
    """Convert map graph edges to travel_edges format."""
    edges = map_graph.get("edges", [])
    nodes_by_id = {n["id"]: n for n in map_graph.get("nodes", [])}
    travel_edges = []
    for e in edges:
        from_node = nodes_by_id.get(e["from"], {})
        to_node = nodes_by_id.get(e["to"], {})
        travel_edges.append({
            "from": from_node.get("name", e["from"]),
            "from_id": e["from"],
            "to": to_node.get("name", e["to"]),
            "to_id": e["to"],
            "tier": "short",
        })
    return travel_edges


def apply_procedural_world(state: dict[str, Any], rng: Any) -> None:
    """Apply procedural worldgen to state."""
    world = state.setdefault("world", {})
    seed = world.get("seed", 0)
    setting = state.get("world_bible", {}).get("setting_primary", "medieval_fantasy")

    map_graph = generate_world(seed, setting)
    world["procedural_map"] = map_graph
    world["travel_edges"] = map_to_travel_edges(map_graph)
    world["generated"] = True

    # Set starting location
    nodes = map_graph.get("nodes", [])
    if nodes:
        start = nodes[0]
        world["location"] = start["name"]
        world["location_id"] = start["id"]
        start["visited"] = True


def sync_current_location_from_map(state: dict[str, Any]) -> None:
    """Sync location name from procedural map if available."""
    world = state.get("world", {})
    loc_id = world.get("location_id", "")
    nodes = world.get("procedural_map", {}).get("nodes", [])
    for node in nodes:
        if node["id"] == loc_id:
            world["location"] = node["name"]
            return


def reveal_lore_fragment(state: dict[str, Any], node_id: str) -> str:
    """Reveal and return lore for a node."""
    world = state.get("world", {})
    nodes = world.get("procedural_map", {}).get("nodes", [])
    for node in nodes:
        if node["id"] == node_id:
            node["lore_revealed"] = True
            return node.get("lore", "Nothing notable here.")
    return "This place holds no secrets."


def format_map(state: dict[str, Any]) -> str:
    """Format a text-based map display."""
    world = state.get("world", {})
    nodes = world.get("procedural_map", {}).get("nodes", [])
    edges = world.get("procedural_map", {}).get("edges", [])
    current_id = world.get("location_id", "")

    if not nodes:
        return "No map data."

    lines = ["**World Map:**"]
    for node in nodes:
        marker = "📍" if node["id"] == current_id else ("✅" if node.get("visited") else "❓")
        lines.append(f"  {marker} {node['name']} ({node['biome']})")

    if edges:
        lines.append("\n**Connections:**")
        for e in edges[:20]:  # limit display
            lines.append(f"  {e['from']} ↔ {e['to']}")

    return "\n".join(lines)


def graph_is_connected(edges: list[dict]) -> bool:
    """Verify the map graph is connected using BFS."""
    if not edges:
        return True  # trivially connected (0 or 1 node)

    adj: dict[str, set[str]] = {}
    for e in edges:
        adj.setdefault(e["from"], set()).add(e["to"])
        adj.setdefault(e["to"], set()).add(e["from"])

    nodes = set(adj.keys())
    if not nodes:
        return True

    start = next(iter(nodes))
    visited = {start}
    queue = deque([start])
    while queue:
        curr = queue.popleft()
        for neighbor in adj.get(curr, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited == nodes
