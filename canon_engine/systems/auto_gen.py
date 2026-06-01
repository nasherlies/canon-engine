"""auto_gen.py — Auto-generates rich starting content for new games.

Generates: opening scenario, starting gear, companions, skills, first quest,
all contextualised by genre, location, race, and class.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

_CONTENT = Path(__file__).resolve().parent.parent.parent / "content"


# ── Genre-specific scenario templates ────────────────────────────────────────

_SCENARIO_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "medieval_fantasy": {
        "openings": [
            "The {time_of_day} sun filters through the stained glass of {location}, casting jeweled light across worn stone floors. The smell of {smell} hangs heavy in the air. {hook}",
            "Rain hammers the cobblestones outside {location}. A fire crackles in the hearth while {npc_count} strangers nurse their drinks. {hook}",
            "You push open the heavy oak door of {location}. The room falls silent for a heartbeat — then resumes, louder than before. {hook}",
            "A funeral procession passes outside {location} as you settle into your seat. The dead man's name is on everyone's lips. {hook}",
        ],
        "hooks": [
            "A hooded figure in the corner catches your eye and slides a sealed envelope across the table toward you.",
            "The innkeeper leans close and whispers: 'You look like someone who solves problems. I have one that pays well.'",
            "A messenger bursts through the door, rain-soaked and breathless, scanning the room — then locks eyes with you.",
            "Your companion taps your arm and nods toward the door, where a wanted poster bears a face you recognise.",
            "A merchant's cart has overturned outside, spilling exotic goods across the road. People are already grabbing what they can.",
            "An old woman at the bar turns to you with milky eyes and says: 'The dead walk in the eastern marshes. Someone must stop them.'",
            "A fight breaks out between two drunks. One of them drops a map with your destination circled in red ink.",
        ],
        "smells": [
            "roasting meat and spilled ale", "woodsmoke and wet wool",
            "old parchment and candle wax", "horse sweat and iron",
            "fresh bread and lavender", "incense and damp stone",
        ],
    },
    "space_opera": {
        "openings": [
            "The neon haze of {location} hums with the chatter of a hundred species. Holographic ads flicker overhead. {hook}",
            "Your boots clank on the grated floor of {location}. The recycled air tastes like ozone and engine grease. {hook}",
            "Alarms blare across {location} as a damaged freighter limps into docking bay 7. {hook}",
            "The captain's lounge aboard {location} is packed with off-duty spacers. Someone's losing badly at holo-chess. {hook}",
        ],
        "hooks": [
            "A bounty hologram flickers to life on your comm — the target is someone you used to call a friend.",
            "Your ship's AI chirps: 'Incoming transmission from an unregistered frequency. Shall I accept?'",
            "A xenobiologist rushes toward you, clutching a specimen container that's glowing an unhealthy shade of green.",
            "The bartender slides you a drink you didn't order. Under the glass is a data chip and a single word: RUN.",
            "An explosion rocks the station. Through the viewport, you see a pirate vessel decloaking.",
            "A street urchin bumps into you — and you feel a datastick slip into your pocket.",
        ],
        "smells": [
            "recycled air and machine oil", "synthetic noodles and ion discharge",
            "antiseptic and sweat", "burnt circuitry and ozone",
        ],
    },
    "gothic_horror": {
        "openings": [
            "Fog coils around the iron gates of {location}. Somewhere inside, a bell tolls. {hook}",
            "The floorboards of {location} groan under your weight. Every shadow seems to breathe. {hook}",
            "You arrive at {location} as the last light dies. The caretaker is long gone — only his journal remains. {hook}",
            "Candles gutter in the hallway of {location}. Something scratches behind the walls. {hook}",
        ],
        "hooks": [
            "A child's laughter echoes from the empty nursery upstairs. There are no children here.",
            "You find a portrait on the wall — the face is yours, but the painting is over a century old.",
            "The mirror at the end of the hall doesn't show your reflection. It shows something else watching you.",
            "A bloodstained letter on the table reads: 'If you're reading this, it already knows you're here.'",
            "The church bell rings thirteen times. The locals say that means the dead are hungry.",
        ],
        "smells": [
            "damp rot and old blood", "mildew and extinguished candles",
            "embalming herbs and wet earth", "iron and decay",
        ],
    },
    "western": {
        "openings": [
            "The wind howls through the main street of {location}. Tumbleweeds roll past a sun-bleached wanted poster. {hook}",
            "You push through the swinging doors of {location}. Every head turns. The piano player stops mid-note. {hook}",
            "Dust devils dance outside {location}. Inside, a poker game has been going for three days straight. {hook}",
            "The stagecoach drops you at the edge of {location}. The driver tips his hat: 'Good luck, stranger.' {hook}",
        ],
        "hooks": [
            "The sheriff approaches you with a tired expression: 'I need someone who can shoot straight. You interested?'",
            "A woman in a red dress catches your eye from across the saloon and slides a note under her glass.",
            "Your horse rears up suddenly — there's a rattlesnake in the road. And behind it, three riders who don't look friendly.",
            "The undertaker sizes you up as you walk past his shop. 'Fresh face,' he mutters. 'Hope I don't see you again soon.'",
        ],
        "smells": [
            "horse leather and sage", "whiskey and gunpowder",
            "dust and wood smoke", "sweat and leather",
        ],
    },
    "anime_dramatic": {
        "openings": [
            "Cherry blossoms drift across the courtyard of {location}. Students rush past, chattering about the upcoming tournament. {hook}",
            "The academy gates of {location} tower above you. A stern instructor waits at the entrance, clipboard in hand. {hook}",
            "Morning light streams through the windows of {location}. Today is the day everything changes. {hook}",
        ],
        "hooks": [
            "A mysterious transfer student arrives — and they're staring directly at you with an unsettling intensity.",
            "Your childhood rival blocks your path: 'I've been training. Let's settle this once and for all.'",
            "A small creature materialises on your shoulder. It speaks in riddles and demands to be called 'Lord Fluffington.'",
            "The headmaster's voice booms over the intercom: 'All students to the arena. An emergency evaluation begins now.'",
        ],
        "smells": [
            "cherry blossoms and clean air", "polished wood and green tea",
            "incense and fresh rain", "ink and parchment",
        ],
    },
    "post_apocalyptic": {
        "openings": [
            "The dust never really settles in {location}. Scavengers pick through the ruins like vultures. {hook}",
            "You shelter in the husk of {location}. The Geiger counter clicks softly in your pocket. {hook}",
            "The settlement of {location} is barely standing — but it's the closest thing to civilization for a hundred miles. {hook}",
        ],
        "hooks": [
            "A trader offers you clean water in exchange for a favour. In this world, that's practically charity.",
            "Your radio crackles to life: 'This is Outpost Delta. We have survivors. Requesting immediate—' Static.",
            "A child tugs your sleeve and points to the horizon. A dust cloud is approaching. It's either raiders or salvation.",
        ],
        "smells": [
            "dust and diesel fumes", "charred metal and ash",
            "rotting vegetation and rust", "smoke and stale water",
        ],
    },
    "cyberpunk": {
        "openings": [
            "Rain and neon blur together outside {location}. Your neural implant buzzes with unfiltered data. {hook}",
            "The bass shakes the walls of {location}. Holographic dancers flicker above the crowd. {hook}",
            "You jack into the terminal at {location}. The Net sprawls before you — vast, electric, and dangerous. {hook}",
        ],
        "hooks": [
            "A glitch in your implant shows you a face that shouldn't exist — someone who died three years ago.",
            "Your fixer sends a priority ping: 'Job. High risk. High pay. Interested? Reply Y or your debt gets called in.'",
            "Corporate drones flood the street. Someone in the crowd grabs your arm: 'They're after me. Please — hide me.'",
        ],
        "smells": [
            "synthetic noodles and acid rain", "circuitry and cheap perfume",
            "exhaust fumes and ozone", "blood and battery acid",
        ],
    },
}


# ── Companion templates by genre ─────────────────────────────────────────────

_COMPANION_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "medieval_fantasy": [
        {"role": "warrior", "personality": "warrior", "desc": "a grizzled sellsword with a code of honor", "stats": {"STR": 15, "DEX": 12, "CON": 14, "INT": 9, "CHA": 10, "LCK": 11}},
        {"role": "healer", "personality": "scholar", "desc": "a wandering cleric with a dark past", "stats": {"STR": 8, "DEX": 10, "CON": 12, "INT": 15, "CHA": 14, "LCK": 10}},
        {"role": "rogue", "personality": "rogue", "desc": "a charming thief with fingers faster than thought", "stats": {"STR": 10, "DEX": 16, "CON": 11, "INT": 13, "CHA": 14, "LCK": 12}},
        {"role": "ranger", "personality": "ranger", "desc": "a silent archer bonded to a grey wolf", "stats": {"STR": 12, "DEX": 15, "CON": 13, "INT": 11, "CHA": 8, "LCK": 13}},
        {"role": "mage", "personality": "scholar", "desc": "a young hedge-wizard chasing forbidden knowledge", "stats": {"STR": 7, "DEX": 10, "CON": 10, "INT": 16, "CHA": 12, "LCK": 11}},
    ],
    "space_opera": [
        {"role": "pilot", "personality": "warrior", "desc": "a hotshot pilot with a bounty on three systems", "stats": {"STR": 10, "DEX": 15, "CON": 12, "INT": 13, "CHA": 14, "LCK": 13}},
        {"role": "medic", "personality": "scholar", "desc": "a xenobiologist who's seen too much", "stats": {"STR": 8, "DEX": 11, "CON": 11, "INT": 16, "CHA": 12, "LCK": 10}},
        {"role": "mechanic", "personality": "ranger", "desc": "a grease-stained engineer who talks to machines", "stats": {"STR": 12, "DEX": 13, "CON": 13, "INT": 14, "CHA": 9, "LCK": 11}},
        {"role": "mercenary", "personality": "warrior", "desc": "a cybernetically enhanced gun-for-hire", "stats": {"STR": 14, "DEX": 14, "CON": 14, "INT": 10, "CHA": 8, "LCK": 12}},
    ],
    "gothic_horror": [
        {"role": "occultist", "personality": "scholar", "desc": "a nervous scholar who knows too much about the darkness", "stats": {"STR": 7, "DEX": 10, "CON": 10, "INT": 16, "CHA": 12, "LCK": 9}},
        {"role": "hunter", "personality": "warrior", "desc": "a monster hunter with silvered weapons and scars to match", "stats": {"STR": 14, "DEX": 13, "CON": 14, "INT": 11, "CHA": 10, "LCK": 12}},
        {"role": "medium", "personality": "ranger", "desc": "a quiet medium who hears the voices of the dead", "stats": {"STR": 8, "DEX": 11, "CON": 10, "INT": 14, "CHA": 15, "LCK": 8}},
    ],
    "western": [
        {"role": "gunslinger", "personality": "warrior", "desc": "a quick-draw artist with a price on their head", "stats": {"STR": 12, "DEX": 16, "CON": 13, "INT": 10, "CHA": 12, "LCK": 14}},
        {"role": "preacher", "personality": "scholar", "desc": "a traveling preacher who packs a Bible and a derringer", "stats": {"STR": 10, "DEX": 11, "CON": 12, "INT": 13, "CHA": 15, "LCK": 11}},
        {"role": "tracker", "personality": "ranger", "desc": "a silent tracker who reads the land like a book", "stats": {"STR": 13, "DEX": 14, "CON": 14, "INT": 12, "CHA": 8, "LCK": 13}},
    ],
    "anime_dramatic": [
        {"role": "rival", "personality": "warrior", "desc": "your intense childhood rival with hidden respect for you", "stats": {"STR": 14, "DEX": 14, "CON": 13, "INT": 12, "CHA": 14, "LCK": 12}},
        {"role": "support", "personality": "scholar", "desc": "a loyal friend who believes in you more than anyone", "stats": {"STR": 8, "DEX": 10, "CON": 11, "INT": 14, "CHA": 16, "LCK": 11}},
        {"role": "mysterious", "personality": "ranger", "desc": "a transfer student with a mysterious power and a secret agenda", "stats": {"STR": 12, "DEX": 13, "CON": 12, "INT": 15, "CHA": 13, "LCK": 10}},
    ],
    "post_apocalyptic": [
        {"role": "scavenger", "personality": "rogue", "desc": "a resourceful scavenger who knows every ruin within fifty miles", "stats": {"STR": 11, "DEX": 15, "CON": 13, "INT": 13, "CHA": 10, "LCK": 14}},
        {"role": "medic", "personality": "scholar", "desc": "a pre-war medic with steady hands and haunted eyes", "stats": {"STR": 9, "DEX": 12, "CON": 11, "INT": 15, "CHA": 12, "LCK": 10}},
        {"role": "enforcer", "personality": "warrior", "desc": "a raider-turned-protector with a blood-soaked past", "stats": {"STR": 15, "DEX": 12, "CON": 15, "INT": 8, "CHA": 10, "LCK": 11}},
    ],
    "cyberpunk": [
        {"role": "netrunner", "personality": "scholar", "desc": "a paranoid netrunner who trusts code more than people", "stats": {"STR": 8, "DEX": 12, "CON": 10, "INT": 16, "CHA": 10, "LCK": 11}},
        {"role": "street_samurai", "personality": "warrior", "desc": "a chrome-limbed street samurai with a debt to pay", "stats": {"STR": 14, "DEX": 15, "CON": 13, "INT": 10, "CHA": 11, "LCK": 12}},
        {"role": "fixer", "personality": "rogue", "desc": "a smooth-talking fixer who knows everyone's secrets", "stats": {"STR": 9, "DEX": 11, "CON": 10, "INT": 14, "CHA": 16, "LCK": 13}},
    ],
}


# ── Genre-appropriate starting quests ────────────────────────────────────────

_STARTER_QUESTS: Dict[str, List[Dict[str, Any]]] = {
    "medieval_fantasy": [
        {"title": "The Missing Caravan", "desc": "A merchant's caravan vanished on the road to {destination}. Investigate what happened and recover the cargo.", "objectives": ["Travel to the trade road", "Find the missing caravan", "Deal with whatever you find"], "reward_gold": 75, "reward_xp": 100},
        {"title": "Rats in the Cellar", "desc": "The innkeeper swears something is living in the cellar. It's not rats — it's worse.", "objectives": ["Enter the cellar", "Find the source of the disturbance", "Report back to the innkeeper"], "reward_gold": 40, "reward_xp": 60},
        {"title": "The Stranger's Request", "desc": "A hooded stranger offers gold for a simple job: deliver a sealed letter. No questions asked.", "objectives": ["Accept the letter", "Deliver it to the marked address", "Return for your payment"], "reward_gold": 50, "reward_xp": 70},
    ],
    "space_opera": [
        {"title": "Ghost Signal", "desc": "Your ship's sensors picked up a distress beacon from a derelict freighter. Someone — or something — is still broadcasting.", "objectives": ["Locate the signal source", "Board the derelict", "Survive what's inside"], "reward_gold": 100, "reward_xp": 120},
        {"title": "The Informant", "desc": "A contact in the lower decks has information about a pirate fleet. But they want extraction first.", "objectives": ["Navigate to the lower decks", "Find and extract the informant", "Get them to safety"], "reward_gold": 80, "reward_xp": 90},
    ],
    "gothic_horror": [
        {"title": "The Locked Room", "desc": "There's a room in {location} that's been sealed for decades. Something inside has started scratching at the door.", "objectives": ["Find the key to the room", "Enter the locked room", "Discover what's been scratching"], "reward_gold": 50, "reward_xp": 80},
        {"title": "The Missing Villagers", "desc": "Three villagers vanished last night. Their homes are untouched. Their beds are still warm.", "objectives": ["Search the missing villagers' homes", "Follow the trail", "Find the villagers — or what's left of them"], "reward_gold": 60, "reward_xp": 90},
    ],
    "western": [
        {"title": "The Bounty", "desc": "Dead or alive — a notorious outlaw was last seen heading toward {destination}. The sheriff wants them brought in.", "objectives": ["Track the outlaw", "Confront them", "Bring them back to the sheriff"], "reward_gold": 100, "reward_xp": 110},
        {"title": "Water Rights", "desc": "Someone's poisoning the town well. The ranchers are pointing fingers. Find the truth before the town tears itself apart.", "objectives": ["Investigate the well", "Gather evidence", "Confront the guilty party"], "reward_gold": 60, "reward_xp": 80},
    ],
    "anime_dramatic": [
        {"title": "The Entrance Exam", "desc": "Prove yourself at the academy's annual combat trials. Only the top fighters advance.", "objectives": ["Register for the trials", "Win your first match", "Advance to the next round"], "reward_gold": 50, "reward_xp": 120},
        {"title": "The Mysterious Transfer", "desc": "A new student arrived under strange circumstances. The headmaster wants you to keep an eye on them.", "objectives": ["Meet the transfer student", "Learn their secret", "Report your findings"], "reward_gold": 40, "reward_xp": 80},
    ],
    "post_apocalyptic": [
        {"title": "Clean Water", "desc": "The settlement's water purifier is broken. A replacement part exists in the old factory — if you can reach it.", "objectives": ["Travel to the old factory", "Find the replacement part", "Return it to the settlement"], "reward_gold": 60, "reward_xp": 90},
        {"title": "The Radio Signal", "desc": "A repeating broadcast from across the wasteland promises shelter and supplies. Is it real, or a raider trap?", "objectives": ["Follow the signal", "Reach the source", "Discover the truth"], "reward_gold": 80, "reward_xp": 100},
    ],
    "cyberpunk": [
        {"title": "The Dead Drop", "desc": "Your fixer has a job: pick up a package from a dead drop in hostile territory. Simple. Except three other crews want it too.", "objectives": ["Locate the dead drop", "Secure the package", "Deliver it to your fixer"], "reward_gold": 100, "reward_xp": 100},
        {"title": "Ghost in the Machine", "desc": "Someone hacked your implant while you slept. Find out who, and why, before they do it again.", "objectives": ["Trace the hack", "Find the hacker", "Settle the score"], "reward_gold": 75, "reward_xp": 90},
    ],
}


# ── Class-to-skill-tree mapping ──────────────────────────────────────────────

_CLASS_TREE_MAP: Dict[str, str] = {
    "knight": "warrior",
    "warrior": "warrior",
    "paladin": "warrior",
    "barbarian": "warrior",
    "rogue": "rogue",
    "thief": "rogue",
    "assassin": "rogue",
    "bard": "rogue",
    "mage": "mage",
    "wizard": "mage",
    "warlock": "mage",
    "sorcerer": "mage",
    "ranger": "ranger",
    "druid": "ranger",
    "archer": "ranger",
    "hunter": "ranger",
    "engineer": "mage",   # tech = mage equivalent
    "pilot": "ranger",
    "medic": "mage",
    "gunslinger": "ranger",
    "mechanic": "ranger",
    "netrunner": "mage",
    "mercenary": "warrior",
    "soldier": "warrior",
    "scavenger": "rogue",
    "enforcer": "warrior",
}

# Class-to-kit mapping (for starting_kits.json)
_CLASS_KIT_MAP: Dict[str, str] = {
    "knight": "knight",
    "warrior": "knight",
    "paladin": "knight",
    "barbarian": "knight",
    "soldier": "knight",
    "enforcer": "knight",
    "mercenary": "knight",
    "rogue": "rogue",
    "thief": "rogue",
    "assassin": "rogue",
    "bard": "rogue",
    "scavenger": "rogue",
    "mage": "mage",
    "wizard": "mage",
    "warlock": "mage",
    "sorcerer": "mage",
    "engineer": "mage",
    "netrunner": "mage",
    "medic": "mage",
    "ranger": "ranger",
    "druid": "ranger",
    "archer": "ranger",
    "hunter": "ranger",
    "pilot": "ranger",
    "mechanic": "ranger",
    "gunslinger": "ranger",
}

# Genre-specific gear overrides
_GENRE_GEAR_OVERRIDES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "space_opera": {
        "_any": [
            {"name": "Plasma Pistol", "rarity": "common", "itype": "weapon", "weight": 1.5, "equip_slot": "weapon_main", "effects": {"damage": 7}},
            {"name": "Enviro-Suit", "rarity": "common", "itype": "armor", "weight": 3.0, "equip_slot": "chest_armor", "effects": {"defense": 4}},
            {"name": "Med-Kit", "rarity": "common", "itype": "consumable", "weight": 0.5, "qty": 2, "consumable": True, "effects": {"heal_hp": 25}},
        ],
    },
    "gothic_horror": {
        "_any": [
            {"name": "Silvered Blade", "rarity": "uncommon", "itype": "weapon", "weight": 2.0, "equip_slot": "weapon_main", "effects": {"damage": 6, "bonus_vs_undead": 4}},
            {"name": "Lantern", "rarity": "common", "itype": "tool", "weight": 1.5, "qty": 1},
            {"name": "Holy Water", "rarity": "common", "itype": "consumable", "weight": 0.5, "qty": 3, "consumable": True, "effects": {"damage_undead": 15}},
        ],
    },
    "western": {
        "_any": [
            {"name": "Colt Revolver", "rarity": "common", "itype": "weapon", "weight": 2.0, "equip_slot": "weapon_main", "effects": {"damage": 8}},
            {"name": "Leather Duster", "rarity": "common", "itype": "armor", "weight": 4.0, "equip_slot": "chest_armor", "effects": {"defense": 3}},
            {"name": "Bandage Roll", "rarity": "common", "itype": "consumable", "weight": 0.3, "qty": 3, "consumable": True, "effects": {"heal_hp": 15}},
        ],
    },
    "cyberpunk": {
        "_any": [
            {"name": "Monofilament Blade", "rarity": "uncommon", "itype": "weapon", "weight": 1.0, "equip_slot": "weapon_main", "effects": {"damage": 9}},
            {"name": "Subdermal Armor", "rarity": "common", "itype": "armor", "weight": 0.0, "equip_slot": "chest_armor", "effects": {"defense": 4}},
            {"name": "Stim Patch", "rarity": "common", "itype": "consumable", "weight": 0.2, "qty": 3, "consumable": True, "effects": {"heal_hp": 20}},
        ],
    },
    "anime_dramatic": {
        "_any": [
            {"name": "Training Blade", "rarity": "common", "itype": "weapon", "weight": 2.0, "equip_slot": "weapon_main", "effects": {"damage": 6}},
            {"name": "Academy Uniform", "rarity": "common", "itype": "armor", "weight": 2.0, "equip_slot": "chest_armor", "effects": {"defense": 2}},
            {"name": "Healing Herb", "rarity": "common", "itype": "consumable", "weight": 0.2, "qty": 3, "consumable": True, "effects": {"heal_hp": 20}},
        ],
    },
    "post_apocalyptic": {
        "_any": [
            {"name": "Pipe Rifle", "rarity": "common", "itype": "weapon", "weight": 3.0, "equip_slot": "weapon_main", "effects": {"damage": 7}},
            {"name": "Scrap Armor", "rarity": "common", "itype": "armor", "weight": 6.0, "equip_slot": "chest_armor", "effects": {"defense": 4}},
            {"name": "Stimpak", "rarity": "common", "itype": "consumable", "weight": 0.5, "qty": 2, "consumable": True, "effects": {"heal_hp": 25}},
        ],
    },
}

# Generic fallback gear for any class
_GENERIC_GEAR = [
    {"name": "Adventurer's Pack", "rarity": "common", "itype": "misc", "weight": 2.0, "qty": 1},
    {"name": "Health Potion", "rarity": "common", "itype": "consumable", "weight": 0.5, "qty": 3, "consumable": True, "effects": {"heal_hp": 25}},
    {"name": "Torch", "rarity": "common", "itype": "tool", "weight": 1.0, "qty": 2},
    {"name": "Rations (3 days)", "rarity": "common", "itype": "consumable", "weight": 2.0, "qty": 1},
    {"name": "Rope (50ft)", "rarity": "common", "itype": "tool", "weight": 2.0, "qty": 1},
]


# ── Genre NPC name pools ─────────────────────────────────────────────────────

_NPC_NAMES: Dict[str, List[str]] = {
    "medieval_fantasy": ["Aldric", "Brenna", "Caelan", "Dagna", "Eldon", "Freya", "Gareth", "Helga", "Ivar", "Kael", "Lyra", "Maren", "Orin", "Petra", "Roric", "Sigrid", "Theron", "Vera", "Wren"],
    "space_opera": ["Zara", "Kael", "Nova", "Rex", "Drake", "Astra", "Orion", "Vex", "Sable", "Pax", "Juno", "Cass", "Neo", "Blaze", "Echo", "Flint", "Halo", "Jett"],
    "gothic_horror": ["Elara", "Viktor", "Isolde", "Mortimer", "Lenore", "Dimitri", "Carmilla", "Sebastian", "Ophelia", "Roderick", "Lucinda", "Cornelius"],
    "western": ["Jedediah", "Clementine", "Wyatt", "Belle", "Hank", "Sadie", "Cole", "Josephine", "Buck", "Annie", "Dutch", "Mae"],
    "anime_dramatic": ["Haruki", "Sakura", "Ren", "Yuki", "Takeshi", "Hana", "Kaito", "Mei", "Sora", "Rin", "Akira", "Mio"],
    "post_apocalyptic": ["Ash", "Bones", "Cricket", "Dusty", "Ember", "Flint", "Ghost", "Hawk", "Iron", "Jinx", "Lucky", "Torch"],
    "cyberpunk": ["Chrome", "Data", "Edge", "Flash", "Hex", "Ion", "Jade", "Killswitch", "Link", "Mesh", "Pixel", "Sync", "Trace", "Vox"],
}


def _time_of_day(minutes: int) -> str:
    """Convert world time minutes to time-of-day string."""
    hour = (minutes // 60) % 24
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _pick_random(pool: list, rng: Optional[random.Random] = None) -> Any:
    """Pick a random item from a pool."""
    r = rng or random
    return r.choice(pool) if pool else None


# ── Public API ───────────────────────────────────────────────────────────────

def generate_starting_kit(
    archetype: str,
    genre: str = "medieval_fantasy",
    rng: Optional[random.Random] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Return (inventory, equip) for a given class and genre.

    Tries genre-specific gear first, then falls back to starting_kits.json,
    then generic gear.
    """
    r = rng or random

    # Check genre-specific overrides first
    genre_gear = _GENRE_GEAR_OVERRIDES.get(genre, {})
    if "_any" in genre_gear:
        base_gear = list(genre_gear["_any"])
        # Add class-appropriate extras
        kit_key = _CLASS_KIT_MAP.get(archetype.lower(), "")
        kits_path = _CONTENT / "presets" / "starting_kits.json"
        if kits_path.exists() and kit_key:
            try:
                kits = json.loads(kits_path.read_text(encoding="utf-8"))
                kit = kits.get(kit_key, {})
                # Add consumables and tools from the class kit
                for item in kit.get("inventory", []):
                    if item.get("itype") in ("consumable", "tool") and item["name"] not in [i["name"] for i in base_gear]:
                        base_gear.append(item)
                return base_gear, {}
            except Exception:
                pass
        return base_gear, {}

    # Try class kit from starting_kits.json
    kit_key = _CLASS_KIT_MAP.get(archetype.lower(), archetype.lower())
    kits_path = _CONTENT / "presets" / "starting_kits.json"
    if kits_path.exists():
        try:
            kits = json.loads(kits_path.read_text(encoding="utf-8"))
            kit = kits.get(kit_key, {})
            if kit:
                inv = kit.get("inventory", _GENERIC_GEAR)
                equip = kit.get("equip", {})
                return list(inv), dict(equip)
        except Exception:
            pass

    # Fallback to generic
    return list(_GENERIC_GEAR), {}


def generate_companions(
    genre: str = "medieval_fantasy",
    count: int = 1,
    rng: Optional[random.Random] = None,
) -> List[Dict[str, Any]]:
    """Generate 1-2 starting companions based on genre."""
    r = rng or random
    templates = _COMPANION_TEMPLATES.get(genre, _COMPANION_TEMPLATES["medieval_fantasy"])
    names = _NPC_NAMES.get(genre, _NPC_NAMES["medieval_fantasy"])

    companions = []
    chosen = r.sample(templates, min(count, len(templates)))

    for tmpl in chosen:
        name = r.choice([n for n in names if n not in [c.get("name") for c in companions]])
        companions.append({
            "name": name,
            "role": tmpl["role"],
            "personality": tmpl["personality"],
            "description": tmpl["desc"],
            "level": 1,
            "hp": 40 + tmpl["stats"].get("CON", 10) * 2,
            "max_hp": 40 + tmpl["stats"].get("CON", 10) * 2,
            "stats": tmpl["stats"],
            "loyalty": 25,  # out of 100
            "xp": 0,
            "skills": [],
            "equipment": {},
            "conditions": [],
        })

    return companions


def generate_starter_skills(
    archetype: str,
    rng: Optional[random.Random] = None,
) -> List[Dict[str, Any]]:
    """Return 1-2 starter skills from the appropriate skill tree."""
    r = rng or random
    tree_id = _CLASS_TREE_MAP.get(archetype.lower(), "warrior")

    skills_path = _CONTENT / "skills_trees.json"
    if not skills_path.exists():
        return []

    try:
        data = json.loads(skills_path.read_text(encoding="utf-8"))
        trees = data.get("skill_trees", {})
        tree = trees.get(tree_id, trees.get("warrior", {}))
        all_skills = tree.get("skills", {})

        # Pick 1-2 skills with no prerequisites (starter skills)
        starters = [
            v for v in all_skills.values()
            if not v.get("prerequisites")
        ]

        chosen = r.sample(starters, min(2, len(starters)))
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "description": s["description"],
                "type": s.get("type", "active"),
                "tree": tree_id,
                "rank": 1,
                "max_rank": s.get("max_rank", 1),
                "effects": s.get("effects", {}),
            }
            for s in chosen
        ]
    except Exception:
        return []


def generate_first_quest(
    genre: str = "medieval_fantasy",
    location: str = "The Crossroads Inn",
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Generate a starter quest appropriate to genre and location."""
    r = rng or random
    quests = _STARTER_QUESTS.get(genre, _STARTER_QUESTS["medieval_fantasy"])
    quest = r.choice(quests)

    title = quest["title"]
    desc = quest["desc"].format(destination=location, location=location)
    objectives = [
        {"text": o, "completed": False}
        for o in quest["objectives"]
    ]

    return {
        "id": f"starter_{genre}_{r.randint(1000,9999)}",
        "title": title,
        "description": desc,
        "objectives": objectives,
        "reward_gold": quest["reward_gold"],
        "reward_xp": quest["reward_xp"],
        "status": "active",
        "turns_remaining": None,  # starter quests don't expire
    }


def generate_opening_scenario(
    genre: str = "medieval_fantasy",
    location: str = "The Crossroads Inn",
    char_name: str = "Adventurer",
    archetype: str = "Adventurer",
    race: str = "Human",
    minutes: int = 480,
    rng: Optional[random.Random] = None,
) -> str:
    """Generate a rich opening narrative paragraph."""
    r = rng or random

    tmpl = _SCENARIO_TEMPLATES.get(genre, _SCENARIO_TEMPLATES["medieval_fantasy"])
    opening = r.choice(tmpl["openings"])
    hook = r.choice(tmpl["hooks"])
    smell = r.choice(tmpl["smells"])
    tod = _time_of_day(minutes)
    npc_count = r.randint(2, 6)

    scenario = opening.format(
        location=location,
        hook=hook,
        smell=smell,
        time_of_day=tod,
        npc_count=npc_count,
    )

    # Add character-specific flavor
    race_str = f" the {race}" if race and race.lower() != "human" else ""
    intro = f"**{char_name}**{race_str} the {archetype} — {scenario}"
    return intro


def generate_full_start(
    char_name: str,
    race: str,
    archetype: str,
    genre: str = "medieval_fantasy",
    location: str = "The Crossroads Inn",
    minutes: int = 480,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Generate ALL starting content in one call.

    Returns dict with keys:
      - inventory, equip: starting gear
      - companions: list of companion dicts
      - skills: list of starter skills
      - quest: first quest dict
      - scenario: opening narrative string
    """
    r = rng or random.Random()

    inventory, equip = generate_starting_kit(archetype, genre, r)
    companions = generate_companions(genre, count=1, rng=r)
    skills = generate_starter_skills(archetype, r)
    quest = generate_first_quest(genre, location, r)
    scenario = generate_opening_scenario(genre, location, char_name, archetype, race, minutes, r)

    return {
        "inventory": inventory,
        "equip": equip,
        "companions": companions,
        "skills": skills,
        "quest": quest,
        "scenario": scenario,
    }
