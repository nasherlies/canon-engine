// handbook.js — Player Manual
// Canon Engine UI Module

let _modal = null;
let _currentTopic = 'getting_started';

const TOPICS = [
  {
    id: 'getting_started',
    title: 'Getting Started',
    content: `Welcome to Canon Engine!

Canon Engine is an AI-powered text RPG where your imagination is the limit. Here's how to get started:

• Type anything in the command input to interact with the world
• Describe your actions naturally: "I open the door" or "I talk to the merchant"
• Use slash commands (/) for quick actions like /look, /inv, /stats
• The side panel shows your character info, inventory, and quests

Your adventure awaits!`
  },
  {
    id: 'action_bar',
    title: 'Action Bar',
    content: `The action bar at the bottom of the screen has quick action buttons:

• LOOK — Examine your surroundings
• INVENTORY — Check your items
• STATS — View character attributes
• MAP — See the world map
• PARTY — View companions
• QUESTS — Check active quests
• HELP — Show all commands

Tap any button to instantly run that command.`
  },
  {
    id: 'slash_commands',
    title: 'Slash Commands',
    content: `Type / in the input to see all available commands:

Combat:
• /attack — Strike the enemy
• /block — Defend yourself
• /flee — Run away
• /fight — Start combat

Exploration:
• /look — Examine surroundings
• /inv — Check inventory
• /map — View world map
• /choices — See branching options

Social:
• /say — Speak dialogue
• /talk — Talk to NPC
• /gift — Give item to NPC

Meta:
• /help — Show all commands
• /stats — View character sheet
• /save — Save game
• /quests — View quest log
• /factions — View faction standings
• /summary — Get session recap`
  },
  {
    id: 'inventory',
    title: 'Inventory',
    content: `Your inventory holds all items you've collected.

• Open with /inv or the Inventory side tab
• Each item shows name, rarity, and weight
• Use Equip to wear weapons/armor
• Use Use to consume items
• Use Drop to discard items
• Watch your weight limit!

Items can be found, bought, crafted, or looted.`
  },
  {
    id: 'stats',
    title: 'Stats',
    content: `Your character has 6 core attributes:

• STR (Strength) — Physical power, melee damage
• DEX (Dexterity) — Agility, accuracy, dodge
• CON (Constitution) — Health, stamina, resistance
• INT (Intelligence) — Magic power, mana
• WIS (Wisdom) — Perception, willpower
• CHA (Charisma) — Social skills, leadership

Level up by gaining XP from quests and combat.`
  },
  {
    id: 'equipment',
    title: 'Equipment',
    content: `Equip items to boost your stats:

• Weapons increase damage and combat abilities
• Armor provides protection and resistances
• Accessories grant special bonuses
• Use /equip <item> to equip from inventory

Equipment affects your combat effectiveness and can unlock new abilities.`
  },
  {
    id: 'combat',
    title: 'Combat',
    content: `Combat is turn-based and tactical:

• /attack — Basic attack against enemy
• /block — Reduce incoming damage
• /flee — Attempt to escape combat
• /fight — Trigger a random encounter
• Use abilities for special attacks
• Manage HP, MP, and stamina wisely

Enemies scale with your level. Boss encounters are especially challenging!`
  },
  {
    id: 'tutorial',
    title: 'Tutorial',
    content: `The tutorial walks you through game basics:

• Step-by-step walkthrough of all systems
• Each step has a title, description, and goal
• Press NEXT to advance, EXIT to skip
• Can be re-triggered from the pause menu

Complete the tutorial to unlock all features.`
  },
  {
    id: 'settings',
    title: 'Settings',
    content: `Customize your experience in Settings:

Gameplay:
• Difficulty (Easy/Normal/Hard)
• Autosave toggle
• Text speed

Display:
• Themes (Dark/Ocean/Forest/Blood)
• Font size and style
• CRT effects and high contrast

Audio:
• Master, music, and SFX volume

API:
• Custom AI provider and model
• API key configuration`
  },
  {
    id: 'saving',
    title: 'Saving',
    content: `Your progress is important!

• Auto-save occurs after each action
• Manual save with /save or pause menu
• Multiple save slots available
• Load saves from the main menu
• Copy, rename, or delete saves

Saves store your character, inventory, quests, and world state.`
  },
  {
    id: 'about',
    title: 'About',
    content: `Canon Engine v0.6.0
AI-Powered Infinite RPG

Canon Engine uses AI to generate dynamic narratives, characters, and worlds. Your choices shape the story in unique ways.

Features:
• Infinite procedural storytelling
• Dynamic NPC interactions
• Multi-genre world building
• Companion system
• Faction reputation
• Quest system
• Lore codex
• Save/load system

Created with imagination and code.`
  }
];

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function createModal() {
  if (_modal) return _modal;
  const modal = document.createElement('div');
  modal.id = 'handbook-modal';
  modal.className = 'modal';
  modal.style.zIndex = '105';
  modal.innerHTML = `
    <div class="modal-box" style="width:700px;max-height:80dvh;display:flex;flex-direction:column;padding:0;">
      <div style="display:flex;justify-content:space-between;align-items:center;padding:16px 24px 8px;border-bottom:1px solid rgba(58,58,92,0.3);">
        <h2 style="margin:0;">📚 PLAYER HANDBOOK</h2>
        <button class="close-btn" id="handbook-close" style="position:static;">&times;</button>
      </div>
      <div style="display:flex;flex:1;min-height:0;">
        <div id="handbook-sidebar" style="
          width:200px;border-right:1px solid rgba(58,58,92,0.3);
          overflow-y:auto;padding:8px 0;flex-shrink:0;
        "></div>
        <div id="handbook-content" style="
          flex:1;overflow-y:auto;padding:16px 24px;line-height:1.6;
        "></div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  modal.querySelector('#handbook-close').addEventListener('click', closeHandbook);
  modal.addEventListener('mousedown', (e) => {
    if (e.target === modal) closeHandbook();
  });

  _modal = modal;
  return modal;
}

function renderSidebar() {
  const sidebar = _modal.querySelector('#handbook-sidebar');
  if (!sidebar) return;

  sidebar.innerHTML = TOPICS.map(topic => {
    const active = topic.id === _currentTopic;
    return `<div data-topic="${topic.id}" style="
      padding:8px 16px;cursor:pointer;font-size:13px;
      color:${active ? '#c8b16c' : '#888'};
      background:${active ? 'rgba(200,177,108,0.08)' : 'transparent'};
      border-left:2px solid ${active ? '#c8b16c' : 'transparent'};
      transition:all 0.15s;
    ">${esc(topic.title)}</div>`;
  }).join('');

  sidebar.querySelectorAll('[data-topic]').forEach(el => {
    el.addEventListener('click', () => selectTopic(el.dataset.topic));
    el.addEventListener('mouseenter', () => {
      if (el.dataset.topic !== _currentTopic) {
        el.style.color = '#a3a3a3';
        el.style.background = 'rgba(200,177,108,0.04)';
      }
    });
    el.addEventListener('mouseleave', () => {
      if (el.dataset.topic !== _currentTopic) {
        el.style.color = '#888';
        el.style.background = 'transparent';
      }
    });
  });
}

function renderContent() {
  const content = _modal.querySelector('#handbook-content');
  if (!content) return;

  const topic = TOPICS.find(t => t.id === _currentTopic);
  if (!topic) {
    content.innerHTML = '<div style="color:#555;font-style:italic;">Select a topic from the sidebar.</div>';
    return;
  }

  // Convert content to HTML with basic formatting
  const html = esc(topic.content)
    .replace(/\n\n/g, '</p><p style="margin-top:12px;">')
    .replace(/\n•/g, '<br>•')
    .replace(/\n/g, '<br>');

  content.innerHTML = `
    <div style="color:#c8b16c;font-size:18px;font-family:Georgia,serif;margin-bottom:12px;">${esc(topic.title)}</div>
    <div style="color:#a3a3a3;font-size:14px;"><p>${html}</p></div>
  `;
}

export function openHandbook() {
  createModal();
  renderSidebar();
  renderContent();
  _modal.classList.add('show');
}

export function closeHandbook() {
  if (_modal) _modal.classList.remove('show');
}

export function selectTopic(topicId) {
  _currentTopic = topicId;
  renderSidebar();
  renderContent();
}

export default { openHandbook, closeHandbook, selectTopic };
