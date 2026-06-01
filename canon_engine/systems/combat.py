"""D&D 5e Combat System for Canon Engine.

Implements proper D&D 5e rules: initiative, attack rolls, damage, crits,
saving throws, dodge action, and enemy AI.

state['combat'] blob:
    active: bool
    enemies: list[dict]  — each has name, display_name, hp, max_hp, ac, attack_bonus, damage_dice, initiative
    active_enemy_index: int  (legacy compat)
    round: int
    turn: str  — 'player' | 'enemy'
    initiative_order: list[dict]  — sorted by initiative, entries: {name, initiative, is_player, index}
    current_turn_index: int  — index into initiative_order
    player_dodging: bool  — True if player used Dodge action
    defeated_enemies: list  — enemies defeated this combat
"""

from __future__ import annotations

import random
from typing import Any


# ---------------------------------------------------------------------------
# Dice utilities
# ---------------------------------------------------------------------------

def _d20() -> int:
    """Roll a single d20."""
    return random.randint(1, 20)


def _roll_dice(expr: str) -> int:
    """Parse 'NdM+K' and roll.  Fallback: return int(expr) or 0."""
    try:
        if "d" in expr:
            parts = expr.replace("-", "+-").split("+")
            total = 0
            for p in parts:
                p = p.strip()
                if "d" in p:
                    n, m = p.split("d", 1)
                    total += sum(random.randint(1, int(m)) for _ in range(int(n or 1)))
                elif p:
                    total += int(p)
            return max(0, total)
        return max(0, int(expr))
    except Exception:
        return 4


def _roll_dice_detail(expr: str) -> tuple[int, list[int]]:
    """Roll dice and return (total, individual_die_rolls) for display."""
    try:
        if "d" in expr:
            parts = expr.replace("-", "+-").split("+")
            total = 0
            all_rolls = []
            for p in parts:
                p = p.strip()
                if "d" in p:
                    n, m = p.split("d", 1)
                    rolls = [random.randint(1, int(m)) for _ in range(int(n or 1))]
                    all_rolls.extend(rolls)
                    total += sum(rolls)
                elif p:
                    total += int(p)
            return max(0, total), all_rolls
        return max(0, int(expr)), []
    except Exception:
        return 4, []


# ---------------------------------------------------------------------------
# Auto-numbering
# ---------------------------------------------------------------------------

def number_enemies(enemies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Auto-number duplicate enemies. If two 'Undead Soldier' exist,
    display as 'Undead Soldier 1' and 'Undead Soldier 2'."""
    counts: dict[str, int] = {}
    for e in enemies:
        counts[e['name']] = counts.get(e['name'], 0) + 1
    numbered: dict[str, int] = {}
    for e in enemies:
        if counts[e['name']] > 1:
            numbered[e['name']] = numbered.get(e['name'], 0) + 1
            e['display_name'] = f"{e['name']} {numbered[e['name']]}"
        else:
            e['display_name'] = e['name']
    return enemies


# ---------------------------------------------------------------------------
# Proficiency bonus (D&D 5e scaling)
# ---------------------------------------------------------------------------

def proficiency_bonus(level: int) -> int:
    """D&D 5e proficiency bonus: 2 + (level - 1) // 4.
    L1-4=+2, L5-8=+3, L9-12=+4, L13-16=+5, L17-20=+6."""
    return 2 + (level - 1) // 4


# ---------------------------------------------------------------------------
# State accessors
# ---------------------------------------------------------------------------

def get_combat(state: dict[str, Any]) -> dict[str, Any]:
    """Get or create the combat state blob."""
    return state.setdefault("combat", {
        "active": False, "enemies": [], "active_enemy_index": 0,
        "round": 0, "turn": "player",
        "initiative_order": [], "current_turn_index": 0,
        "player_dodging": False, "defeated_enemies": [],
    })


def _get_player(state: dict[str, Any]) -> dict[str, Any]:
    """Get player/character dict. Handles both state['player'] and state['character']."""
    return state.get("player", state.get("character", state))


def _get_ability_mod(state: dict[str, Any], ability: str) -> int:
    """Get ability modifier for the player."""
    from canon_engine.systems.character import score_to_modifier
    player = _get_player(state)
    stats = player.get("stats", {})
    return score_to_modifier(stats.get(ability, 10))


def _get_player_ac(state: dict[str, Any]) -> int:
    """Get player AC."""
    return _get_player(state).get("ac", 10)


def _get_player_proficiency(state: dict[str, Any]) -> int:
    """Get player's proficiency bonus (scaled by level)."""
    player = _get_player(state)
    level = player.get("level", 1)
    return proficiency_bonus(level)


# ---------------------------------------------------------------------------
# Initiative System
# ---------------------------------------------------------------------------

def _roll_initiative(state: dict[str, Any], enemies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Roll initiative for all combatants and return sorted initiative order."""
    dex_mod = _get_ability_mod(state, "DEX")
    player_roll = _d20()
    player_init = player_roll + dex_mod

    order = [{
        "name": _get_player(state).get("name", "Player"),
        "initiative": player_init,
        "roll": player_roll,
        "mod": dex_mod,
        "is_player": True,
        "index": -1,
    }]

    for i, enemy in enumerate(enemies):
        e_dex_mod = (enemy.get("dex", 10) - 10) // 2 if "dex" in enemy else 0
        e_roll = _d20()
        e_init = e_roll + e_dex_mod
        enemy["initiative"] = e_init
        order.append({
            "name": enemy.get("display_name", enemy["name"]),
            "initiative": e_init,
            "roll": e_roll,
            "mod": e_dex_mod,
            "is_player": False,
            "index": i,
        })

    # Sort by initiative (descending), ties go to higher DEX
    order.sort(key=lambda x: (-x["initiative"], -x["mod"]))
    return order


def start_combat(state: dict[str, Any], enemies: list[dict[str, Any]]) -> dict[str, Any]:
    """Start combat with the given enemies. Returns narration with initiative order."""
    c = get_combat(state)

    # Auto-number duplicate enemies
    enemies = number_enemies(enemies)

    # Ensure each enemy has damage_dice
    for e in enemies:
        if "damage_dice" not in e:
            e["damage_dice"] = "1d6"
        if "display_name" not in e:
            e["display_name"] = e["name"]

    # Roll initiative
    initiative_order = _roll_initiative(state, enemies)

    # Find player's position in initiative
    player_idx = next(i for i, entry in enumerate(initiative_order) if entry["is_player"])

    c["active"] = True
    c["enemies"] = enemies
    c["active_enemy_index"] = 0
    c["round"] = 1
    c["turn"] = "player"
    c["initiative_order"] = initiative_order
    c["current_turn_index"] = player_idx
    c["player_dodging"] = False
    c["defeated_enemies"] = []

    # Build initiative narration
    player_name = _get_player(state).get("name", "Player")
    narration = "⚔ **Combat Begins!**\n\n🎲 **Initiative:**\n"
    for entry in initiative_order:
        sign = "+" if entry["mod"] >= 0 else ""
        marker = " ← You" if entry["is_player"] else ""
        narration += f"  • {entry['name']}: **{entry['initiative']}** (d20={entry['roll']} + {sign}{entry['mod']}){marker}\n"

    narration += f"\n📜 **Round 1** — {initiative_order[0]['name']} acts first.\n"

    # If player goes first, announce their turn
    if initiative_order[0]["is_player"]:
        narration += _announce_player_turn(state, c)

    return {"narration": narration, "initiative_order": initiative_order}


def _announce_player_turn(state: dict[str, Any], c: dict[str, Any]) -> str:
    """Announce the start of the player's turn."""
    player = _get_player(state)
    hp = player.get("hp", 0)
    max_hp = player.get("max_hp", 0)
    round_num = c.get("round", 1)
    enemies_alive = [e for e in c["enemies"] if e.get("hp", 0) > 0]

    msg = f"\n🕐 **Round {round_num}** — Your turn!\n"
    msg += f"  HP: {hp}/{max_hp} | Actions: **Attack**, **Dodge**, **Use Item**, **Flee**\n"
    enemy_strs = []
    for e in enemies_alive:
        dn = e.get('display_name', e['name'])
        enemy_strs.append(f"{dn} ({e['hp']}/{e['max_hp']} HP)")
    msg += "  Enemies: " + ", ".join(enemy_strs) + "\n"
    return msg


# ---------------------------------------------------------------------------
# Target Resolution
# ---------------------------------------------------------------------------

def _find_target(c: dict[str, Any], target_str: str) -> dict[str, Any] | None:
    """Find an enemy by name or index. Supports substring matching and auto-numbering."""
    if not target_str:
        return None

    enemies = c["enemies"]
    alive = [e for e in enemies if e.get("hp", 0) > 0]
    target_lower = target_str.strip().lower()

    # Try index first (1-based)
    try:
        idx = int(target_lower) - 1
        if 0 <= idx < len(alive):
            return alive[idx]
    except ValueError:
        pass

    # Exact display_name match
    for e in alive:
        if e.get("display_name", "").lower() == target_lower:
            return e

    # Exact name match
    for e in alive:
        if e["name"].lower() == target_lower:
            return e

    # Substring match on display_name
    for e in alive:
        if target_lower in e.get("display_name", "").lower():
            return e

    # Substring match on name
    for e in alive:
        if target_lower in e["name"].lower():
            return e

    return None


def _list_targets(c: dict[str, Any]) -> str:
    """List available targets."""
    alive = [e for e in c["enemies"] if e.get("hp", 0) > 0]
    if not alive:
        return "No enemies remaining."
    lines = ["Available targets:"]
    for i, e in enumerate(alive, 1):
        name = e.get("display_name", e["name"])
        lines.append(f"  {i}. {name} (HP: {e['hp']}/{e['max_hp']}, AC: {e.get('ac', 10)})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Player Actions
# ---------------------------------------------------------------------------

def resolve_player_attack(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    """Player attacks a specific target with D&D 5e rules."""
    c = get_combat(state)
    if not c["active"] or not c["enemies"]:
        return {"narration": "There's nothing to attack."}

    target_str = parsed.get("target", "")
    if not target_str:
        return {"narration": "Attack who? Use `/attack <target name>`\n\n" + _list_targets(c)}

    enemy = _find_target(c, target_str)
    if enemy is None:
        return {"narration": f"Target '{target_str}' not found.\n\n" + _list_targets(c)}

    if enemy.get("hp", 0) <= 0:
        return {"narration": f"{enemy.get('display_name', enemy['name'])} is already defeated!"}

    player = _get_player(state)
    str_mod = _get_ability_mod(state, "STR")
    prof = _get_player_proficiency(state)
    enemy_ac = enemy.get("ac", 10)

    # Attack roll: d20 + STR mod + proficiency
    attack_roll = _d20()
    is_crit = attack_roll == 20
    is_fumble = attack_roll == 1
    attack_total = attack_roll + str_mod + prof

    sign_str = "+" if str_mod >= 0 else ""
    sign_prof = "+" if prof >= 0 else ""

    enemy_name = enemy.get("display_name", enemy["name"])

    if is_fumble:
        narration = (
            f"⚔️ **Attack vs {enemy_name}**\n"
            f"  🎲 You rolled **{attack_total}** (d20=**1** NATURAL 1!{sign_str}{str_mod} STR {sign_prof}{prof} Prof) vs AC {enemy_ac}\n"
            f"  ❌ **Critical Miss!** Your swing goes wide!"
        )
        # After player action, do enemy turns
        narration += _process_enemy_turns(state, c)
        return {"narration": narration}

    if is_crit:
        # Critical hit: double damage dice
        dmg_total, dmg_rolls = _roll_dice_detail("2d8")
        dmg_total = max(0, dmg_total + str_mod)
        enemy["hp"] = max(0, enemy["hp"] - dmg_total)
        narration = (
            f"⚔️ **CRITICAL HIT vs {enemy_name}!**\n"
            f"  🎲 Attack: **{attack_total}** (d20=**{attack_roll}** NAT 20!{sign_str}{str_mod} STR {sign_prof}{prof} Prof) vs AC {enemy_ac}\n"
            f"  💥 Damage: **{dmg_total}** (2d8={dmg_rolls} + {str_mod} STR) — Double dice on crit!\n"
            f"  🩸 {enemy_name}: {enemy['hp']}/{enemy['max_hp']} HP"
        )
    elif attack_total >= enemy_ac:
        # Normal hit
        dmg_total, dmg_rolls = _roll_dice_detail("1d8")
        dmg_total = max(0, dmg_total + str_mod)
        enemy["hp"] = max(0, enemy["hp"] - dmg_total)
        narration = (
            f"⚔️ **Attack vs {enemy_name}**\n"
            f"  🎲 You rolled **{attack_total}** (d20={attack_roll}{sign_str}{str_mod} STR {sign_prof}{prof} Prof) vs AC {enemy_ac} — **HIT!**\n"
            f"  💥 Damage: **{dmg_total}** (1d8={dmg_rolls} + {str_mod} STR)\n"
            f"  🩸 {enemy_name}: {enemy['hp']}/{enemy['max_hp']} HP"
        )
    else:
        # Miss
        narration = (
            f"⚔️ **Attack vs {enemy_name}**\n"
            f"  🎲 You rolled **{attack_total}** (d20={attack_roll}{sign_str}{str_mod} STR {sign_prof}{prof} Prof) vs AC {enemy_ac} — **Miss!**\n"
            f"  Your attack glances off {enemy_name}'s defenses."
        )

    # Check if enemy died
    if enemy["hp"] <= 0:
        narration += f"\n\n💀 **{enemy_name} is defeated!**"
        xp_val = enemy.get("xp_value", 10)
        narration += f" (+{xp_val} XP)"
        c["defeated_enemies"].append(enemy)
        _remove_defeated(c)

        # Check if combat is over
        if not any(e.get("hp", 0) > 0 for e in c["enemies"]):
            narration += _end_combat(state, c)
            return {"narration": narration}

        # Companion banter on kill
        try:
            from canon_engine.systems.companion_banter import on_enemy_kill
            banter = on_enemy_kill(state, enemy=enemy_name)
            if banter:
                narration += "\n\n" + banter
        except Exception:
            pass

    # Process enemy turns (if combat still active)
    if c["active"]:
        narration += _process_enemy_turns(state, c)

    return {"narration": narration}


def resolve_player_dodge(state: dict[str, Any]) -> dict[str, Any]:
    """Player takes the Dodge action. Enemies have disadvantage on attacks."""
    c = get_combat(state)
    if not c["active"]:
        return {"narration": "There's nothing to dodge from."}

    c["player_dodging"] = True
    player = _get_player(state)
    name = player.get("name", "You")

    narration = (
        f"🛡️ **Dodge Action**\n"
        f"  {name} assumes a defensive stance, focusing on evasion.\n"
        f"  *Enemies will have **disadvantage** on attack rolls until your next turn.*\n"
    )

    # Process enemy turns
    narration += _process_enemy_turns(state, c)

    return {"narration": narration}


def resolve_saving_throw(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    """Make a saving throw for the player."""
    ability = parsed.get("ability", "").upper()
    if not ability:
        return {"narration": "Usage: `/save <ability>` (e.g., `/save dex`, `/save con`)"}

    valid_abilities = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    if ability not in valid_abilities:
        return {"narration": f"Invalid ability '{ability}'. Valid: {', '.join(sorted(valid_abilities))}"}

    dc = parsed.get("dc", 12)  # Default DC 12 if not specified

    mod = _get_ability_mod(state, ability)
    roll = _d20()
    total = roll + mod
    success = total >= dc

    sign = "+" if mod >= 0 else ""
    result_emoji = "✅" if success else "❌"
    result_text = "**Success!**" if success else "**Failure!**"

    narration = (
        f"🎲 **{ability} Saving Throw** (DC {dc})\n"
        f"  Rolled: **{total}** (d20={roll}{sign}{mod} {ability}) vs DC {dc}\n"
        f"  {result_emoji} {result_text}"
    )

    return {"narration": narration, "success": success, "total": total}


def resolve_combat_flee(state: dict[str, Any]) -> dict[str, Any]:
    """Attempt to flee combat with DEX check vs DC 13."""
    c = get_combat(state)
    if not c["active"]:
        return {"narration": "There's nothing to flee from."}

    dex_mod = _get_ability_mod(state, "DEX")
    roll = _d20()
    total = roll + dex_mod
    dc = 13

    sign = "+" if dex_mod >= 0 else ""

    if total >= dc:
        # Success — end combat
        c["active"] = False
        narration = (
            f"🏃 **Flee Attempt**\n"
            f"  🎲 DEX Check: **{total}** (d20={roll}{sign}{dex_mod}) vs DC {dc} — **Success!**\n"
            f"  You turn and sprint away, leaving your foes behind!"
        )
        return {"narration": narration}
    else:
        # Fail — enemies get opportunity attacks
        narration = (
            f"🏃 **Flee Attempt**\n"
            f"  🎲 DEX Check: **{total}** (d20={roll}{sign}{dex_mod}) vs DC {dc} — **Failed!**\n"
            f"  Your enemies cut off your retreat!\n"
        )
        # Enemies get opportunity attacks
        narration += _process_opportunity_attacks(state, c)
        return {"narration": narration}


def resolve_turn_status(state: dict[str, Any]) -> dict[str, Any]:
    """Show current combat state: round, turn, initiative order."""
    c = get_combat(state)
    if not c["active"]:
        return {"narration": "You're not in combat."}

    round_num = c.get("round", 1)
    initiative_order = c.get("initiative_order", [])
    current_idx = c.get("current_turn_index", 0)

    player = _get_player(state)
    hp = player.get("hp", 0)
    max_hp = player.get("max_hp", 0)

    current_name = initiative_order[current_idx]["name"] if current_idx < len(initiative_order) else "Unknown"

    narration = f"⚔️ **Combat Status — Round {round_num}**\n\n"
    narration += f"Current turn: **{current_name}**\n"
    narration += f"Your HP: {hp}/{max_hp}\n\n"

    narration += "**Initiative Order:**\n"
    for i, entry in enumerate(initiative_order):
        marker = " ◀ CURRENT" if i == current_idx else ""
        marker += " ← YOU" if entry["is_player"] else ""
        if entry["is_player"]:
            narration += f"  {i+1}. **{entry['name']}** — Init: {entry['initiative']}{marker}\n"
        else:
            enemy_idx = entry.get("index", -1)
            if 0 <= enemy_idx < len(c["enemies"]):
                e = c["enemies"][enemy_idx]
                hp_str = f"{e['hp']}/{e['max_hp']}" if e.get("hp", 0) > 0 else "DEFEATED"
                narration += f"  {i+1}. **{entry['name']}** — Init: {entry['initiative']} (HP: {hp_str}){marker}\n"
            else:
                narration += f"  {i+1}. **{entry['name']}** — Init: {entry['initiative']}{marker}\n"

    narration += f"\n**Actions Available:** Attack, Dodge, Use Item, Flee"
    return {"narration": narration}


# ---------------------------------------------------------------------------
# Enemy AI
# ---------------------------------------------------------------------------

def _enemy_attack_roll(enemy: dict[str, Any], player_ac: int, is_dodging: bool) -> tuple[int, int, bool, bool]:
    """Roll an enemy attack. Returns (attack_roll, attack_total, is_hit, is_crit).
    If dodging, roll twice and take lower (disadvantage)."""
    attack_bonus = enemy.get("attack_bonus", 2)

    if is_dodging:
        # Disadvantage: roll twice, take lower
        roll1 = _d20()
        roll2 = _d20()
        attack_roll = min(roll1, roll2)
    else:
        attack_roll = _d20()

    is_crit = attack_roll == 20
    is_fumble = attack_roll == 1
    attack_total = attack_roll + attack_bonus
    is_hit = not is_fumble and (is_crit or attack_total >= player_ac)

    return attack_roll, attack_total, is_hit, is_crit


def _process_enemy_turns(state: dict[str, Any], c: dict[str, Any]) -> str:
    """Process all enemy turns in initiative order."""
    if not c["active"]:
        return ""

    player = _get_player(state)
    player_ac = _get_player_ac(state)
    is_dodging = c.get("player_dodging", False)
    initiative_order = c.get("initiative_order", [])
    current_idx = c.get("current_turn_index", 0)

    narration = ""
    enemies = c["enemies"]

    # Find all enemies that act after the player in initiative order
    player_name = player.get("name", "Player")

    # Process enemies in initiative order
    for entry in initiative_order:
        if entry["is_player"]:
            continue

        enemy_idx = entry.get("index", -1)
        if enemy_idx < 0 or enemy_idx >= len(enemies):
            continue

        enemy = enemies[enemy_idx]
        if enemy.get("hp", 0) <= 0:
            continue

        # Check if player is dead
        if player.get("hp", 0) <= 0:
            narration += "\n\n💀 **You have fallen in combat...**"
            c["active"] = False
            return narration

        enemy_name = enemy.get("display_name", enemy["name"])
        attack_bonus = enemy.get("attack_bonus", 2)
        damage_dice = enemy.get("damage_dice", "1d6")

        # Attack roll
        attack_roll, attack_total, is_hit, is_crit = _enemy_attack_roll(enemy, player_ac, is_dodging)

        sign_bonus = "+" if attack_bonus >= 0 else ""

        if is_dodging:
            roll_desc = f"d20={attack_roll} (disadvantage){sign_bonus}{attack_bonus}"
        else:
            roll_desc = f"d20={attack_roll}{sign_bonus}{attack_bonus}"

        if is_crit:
            # Critical hit: double damage dice
            dmg_expr = _double_dice(damage_dice)
            dmg_total, dmg_rolls = _roll_dice_detail(dmg_expr)
            from canon_engine.systems.character import apply_damage
            apply_damage(state, dmg_total)
            narration += (
                f"\n\n🗡️ **{enemy_name} attacks!**\n"
                f"  🎲 Rolled **{attack_total}** ({roll_desc}) vs AC {player_ac} — **CRITICAL HIT!**\n"
                f"  💥 Damage: **{dmg_total}** ({dmg_expr}={dmg_rolls})\n"
                f"  🩸 Your HP: {player.get('hp', 0)}/{player.get('max_hp', 0)}"
            )
        elif is_hit:
            # Normal hit
            dmg_total, dmg_rolls = _roll_dice_detail(damage_dice)
            from canon_engine.systems.character import apply_damage
            apply_damage(state, dmg_total)
            narration += (
                f"\n\n🗡️ **{enemy_name} attacks!**\n"
                f"  🎲 Rolled **{attack_total}** ({roll_desc}) vs AC {player_ac} — **Hit!**\n"
                f"  💥 Damage: **{dmg_total}** ({damage_dice}={dmg_rolls})\n"
                f"  🩸 Your HP: {player.get('hp', 0)}/{player.get('max_hp', 0)}"
            )
        else:
            # Miss
            narration += (
                f"\n\n🗡️ **{enemy_name} attacks!**\n"
                f"  🎲 Rolled **{attack_total}** ({roll_desc}) vs AC {player_ac} — **Miss!**\n"
                f"  {enemy_name}'s attack fails to find its mark."
            )

        # Check if player died
        if player.get("hp", 0) <= 0:
            narration += "\n\n💀 **You have fallen in combat...**"
            c["active"] = False
            return narration

    # Reset dodge after enemy turns
    c["player_dodging"] = False

    # Advance round
    c["round"] = c.get("round", 1) + 1

    # Set turn back to player
    player_idx = next((i for i, e in enumerate(initiative_order) if e["is_player"]), 0)
    c["current_turn_index"] = player_idx
    c["turn"] = "player"

    if c["active"]:
        narration += _announce_player_turn(state, c)

    return narration


def _process_opportunity_attacks(state: dict[str, Any], c: dict[str, Any]) -> str:
    """Enemies get opportunity attacks when player fails to flee."""
    player = _get_player(state)
    player_ac = _get_player_ac(state)
    narration = ""

    for enemy in c["enemies"]:
        if enemy.get("hp", 0) <= 0:
            continue

        enemy_name = enemy.get("display_name", enemy["name"])
        attack_bonus = enemy.get("attack_bonus", 2)
        damage_dice = enemy.get("damage_dice", "1d6")

        attack_roll = _d20()
        attack_total = attack_roll + attack_bonus
        sign = "+" if attack_bonus >= 0 else ""

        if attack_roll == 20 or (attack_roll != 1 and attack_total >= player_ac):
            # Hit (opportunity attack)
            if attack_roll == 20:
                dmg_expr = _double_dice(damage_dice)
                dmg_total, dmg_rolls = _roll_dice_detail(dmg_expr)
                crit_text = " (CRIT!)"
            else:
                dmg_total, dmg_rolls = _roll_dice_detail(damage_dice)
                crit_text = ""

            from canon_engine.systems.character import apply_damage
            apply_damage(state, dmg_total)
            narration += (
                f"\n⚡ **Opportunity Attack — {enemy_name}!**\n"
                f"  🎲 Rolled **{attack_total}** (d20={attack_roll}{sign}{attack_bonus}) vs AC {player_ac} — Hit{crit_text}!\n"
                f"  💥 Damage: **{dmg_total}** ({damage_dice}={dmg_rolls})\n"
                f"  🩸 Your HP: {player.get('hp', 0)}/{player.get('max_hp', 0)}"
            )
        else:
            narration += (
                f"\n⚡ **Opportunity Attack — {enemy_name}!**\n"
                f"  🎲 Rolled **{attack_total}** (d20={attack_roll}{sign}{attack_bonus}) vs AC {player_ac} — Miss!\n"
                f"  You slip past {enemy_name}'s guard."
            )

    return narration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _double_dice(expr: str) -> str:
    """Double the dice in an expression for critical hits. '1d6+2' -> '2d6+2'."""
    try:
        if "d" in expr:
            parts = expr.replace("-", "+-").split("+")
            result = []
            for p in parts:
                p = p.strip()
                if "d" in p:
                    n, m = p.split("d", 1)
                    result.append(f"{int(n or 1) * 2}d{m}")
                elif p:
                    result.append(p)
            return "+".join(result)
        return expr
    except Exception:
        return expr


def _remove_defeated(c: dict[str, Any]) -> None:
    """Remove defeated enemies and update indices."""
    c["enemies"] = [e for e in c["enemies"] if e.get("hp", 0) > 0]
    if c["enemies"]:
        c["active_enemy_index"] = min(c["active_enemy_index"], len(c["enemies"]) - 1)
    # Update initiative order indices
    initiative_order = c.get("initiative_order", [])
    # Rebuild indices based on remaining enemies
    alive_names = {e.get("display_name", e["name"]) for e in c["enemies"]}
    c["initiative_order"] = [e for e in initiative_order if e["is_player"] or e["name"] in alive_names]


def _end_combat(state: dict[str, Any], c: dict[str, Any]) -> str:
    """End combat and grant rewards."""
    c["active"] = False
    defeated = c.get("defeated_enemies", [])

    if not defeated:
        return "\n\n🏆 **Combat Ended.**"

    rewards = grant_combat_rewards(state, defeated)
    narration = rewards.get("narration", "")

    # Companion banter on victory
    try:
        from canon_engine.systems.companion_banter import on_combat_victory
        banter = on_combat_victory(state)
        if banter:
            narration += "\n\n" + banter
    except Exception:
        pass

    return narration


# ---------------------------------------------------------------------------
# Legacy compat wrappers (for engine.py which calls these directly)
# ---------------------------------------------------------------------------

def resolve_player_block(state: dict[str, Any]) -> dict[str, Any]:
    """Legacy wrapper: /block now triggers Dodge."""
    return resolve_player_dodge(state)


def enemy_turn_resolve(state: dict[str, Any]) -> dict[str, Any]:
    """Public wrapper for enemy turn (legacy compat)."""
    c = get_combat(state)
    narration = _process_enemy_turns(state, c)
    return {"narration": narration}


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

def grant_combat_rewards(state: dict[str, Any], defeated_enemies: list[dict[str, Any]]) -> dict[str, Any]:
    """Grant XP and loot after defeating enemies."""
    import random
    total_xp = sum(e.get("xp_value", 10) for e in defeated_enemies)
    char = _get_player(state)
    char["xp"] = char.get("xp", 0) + total_xp

    from canon_engine.systems.character import level_up
    level_result = level_up(state)

    reward_text = f"\n\n🏆 **Victory!** +{total_xp} XP"
    if level_result.get("leveled"):
        reward_text += f"\n⬆ **LEVEL UP!** Level {level_result['new_level']}!"
        # Update proficiency bonus on level up
        char["proficiency_bonus"] = proficiency_bonus(level_result["new_level"])

    loot_table = [
        {"name": "Health Potion", "rarity": "common"},
        {"name": "Gold Coins", "rarity": "common"},
        {"name": "Iron Ring", "rarity": "uncommon"},
        {"name": "Enchanted Shard", "rarity": "rare"},
    ]
    roll = random.random()
    item = loot_table[3] if roll > 0.95 else loot_table[2] if roll > 0.85 else loot_table[1] if roll > 0.6 else loot_table[0]

    inventory = char.setdefault("inventory", [])
    existing = next((i for i in inventory if isinstance(i, dict) and i.get("name") == item["name"]), None)
    if existing:
        existing["qty"] = existing.get("qty", 1) + 1
    else:
        inventory.append({**item, "qty": 1})

    reward_text += f"\n🎒 Loot: **{item['name']}** [{item['rarity']}]"
    return {"xp_gained": total_xp, "narration": reward_text}
