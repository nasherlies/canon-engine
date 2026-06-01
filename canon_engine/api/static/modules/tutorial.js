// tutorial.js — Tutorial System
// Canon Engine UI Module

import { show as showToast } from './toast.js';

let _panel = null;
let _steps = [];
let _currentStep = 0;
let _active = false;

const DEFAULT_STEPS = [
  {
    title: 'Welcome',
    description: 'Welcome to Canon Engine! This tutorial will guide you through the basics of the game.',
    goal: 'Press NEXT to continue.'
  },
  {
    title: 'The Command Input',
    description: 'At the bottom of the screen, you\'ll see a text box. Type anything to interact with the world — describe actions, talk to characters, explore.',
    goal: 'Try typing: I look around the tavern'
  },
  {
    title: 'Slash Commands',
    description: 'Type / to see all available commands. Essentials include /help, /stats, /inv, /look, /map, /fight, /save.',
    goal: 'Type / to see the command palette.'
  },
  {
    title: 'The Side Panel',
    description: 'On the right side, you\'ll see tabs for Stats, Inventory, Party, Skills, and Quests. Click any tab or press 1-5 to toggle it.',
    goal: 'Click a side panel tab.'
  },
  {
    title: 'Quick Actions',
    description: 'Above the text input are quick action buttons: LOOK, INVENTORY, STATS, MAP, PARTY, QUESTS, and HELP.',
    goal: 'Tap a quick action button.'
  },
  {
    title: 'The Pause Menu',
    description: 'Click the ☰ MENU button in the top-left corner, or press ESC to open the pause menu.',
    goal: 'Press ESC or click MENU.'
  },
  {
    title: 'Combat',
    description: 'When enemies appear, use /attack, /block, or /flee. Combat is turn-based.',
    goal: 'Type /fight to start a combat encounter.'
  },
  {
    title: 'Saving & Loading',
    description: 'Your game auto-saves after each action. Use /save or the pause menu to manually save. Load saves from the main menu.',
    goal: 'Type /save to save your game.'
  },
  {
    title: 'Settings',
    description: 'Customize themes, font size, audio levels, and API settings from the Settings menu.',
    goal: 'Open Settings from the pause menu.'
  },
  {
    title: 'Tips & Tricks',
    description: 'Be creative! Describe actions in detail. Use /author to set tone, /summary for recaps, /choices for branching options.',
    goal: 'You\'re ready to adventure!'
  }
];

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function createPanel() {
  if (_panel) return _panel;
  const panel = document.createElement('div');
  panel.id = 'tutorial-panel';
  panel.style.cssText = `
    display:none;position:fixed;bottom:60px;left:50%;transform:translateX(-50%);
    background:var(--panel,#1a1a2e);border:2px solid var(--gold,#c8b16c);
    padding:16px 24px;width:480px;max-width:90vw;z-index:95;
    box-shadow:0 0 20px rgba(200,177,108,0.15);
  `;
  panel.innerHTML = `
    <div id="tut-counter" style="color:#555;font-size:11px;letter-spacing:2px;text-align:right;"></div>
    <div id="tut-title" style="color:#c8b16c;font-size:16px;font-weight:bold;margin:8px 0 4px;"></div>
    <div id="tut-desc" style="color:#a3a3a3;font-size:14px;line-height:1.5;margin-bottom:10px;"></div>
    <div id="tut-goal" style="color:#888;font-size:12px;border-top:1px solid rgba(58,58,92,0.3);padding-top:8px;margin-bottom:12px;">
      <span style="color:#555;font-size:10px;letter-spacing:1px;">GOAL:</span>
      <span id="tut-goal-text"></span>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <button id="tut-exit" style="background:none;border:1px solid rgba(58,58,92,0.3);color:#666;padding:6px 16px;cursor:pointer;font-family:inherit;font-size:12px;min-height:36px;">EXIT TUTORIAL</button>
      <button id="tut-next" style="
        background:var(--gold,#c8b16c);color:#000;border:2px solid #b8a050;
        padding:8px 28px;cursor:pointer;font-family:inherit;font-size:14px;font-weight:bold;
        letter-spacing:2px;min-height:40px;
        animation:tutPulse 2s infinite;
      ">NEXT ▸</button>
    </div>
  `;

  // Inject pulse animation
  if (!document.getElementById('tut-pulse-style')) {
    const style = document.createElement('style');
    style.id = 'tut-pulse-style';
    style.textContent = `@keyframes tutPulse{0%,100%{box-shadow:0 0 5px rgba(200,177,108,0.3)}50%{box-shadow:0 0 15px rgba(200,177,108,0.6)}}`;
    document.head.appendChild(style);
  }

  document.body.appendChild(panel);

  panel.querySelector('#tut-next').addEventListener('click', advanceTutorial);
  panel.querySelector('#tut-exit').addEventListener('click', exitTutorial);

  _panel = panel;
  return panel;
}

function renderStep() {
  if (!_panel || !_steps.length) return;
  const step = _steps[_currentStep];
  if (!step) return;

  _panel.querySelector('#tut-counter').textContent = `Step ${_currentStep + 1} of ${_steps.length}`;
  _panel.querySelector('#tut-title').textContent = step.title || '';
  _panel.querySelector('#tut-desc').textContent = step.description || '';
  _panel.querySelector('#tut-goal-text').textContent = step.goal || '';

  const nextBtn = _panel.querySelector('#tut-next');
  if (_currentStep >= _steps.length - 1) {
    nextBtn.textContent = 'DONE ✓';
    nextBtn.style.background = '#33aa33';
    nextBtn.style.borderColor = '#2a8a2a';
  } else {
    nextBtn.textContent = 'NEXT ▸';
    nextBtn.style.background = 'var(--gold,#c8b16c)';
    nextBtn.style.borderColor = '#b8a050';
  }
}

export function openTutorial(steps) {
  _steps = steps || DEFAULT_STEPS;
  _currentStep = 0;
  _active = true;
  createPanel();
  renderStep();
  _panel.style.display = 'block';
}

export function closeTutorial() {
  _active = false;
  if (_panel) _panel.style.display = 'none';
}

export function advanceTutorial() {
  if (!_active) return;
  _currentStep++;
  if (_currentStep >= _steps.length) {
    exitTutorial();
    return;
  }
  renderStep();
}

export function exitTutorial() {
  _active = false;
  if (_panel) _panel.style.display = 'none';
  if (typeof showToast === 'function') {
    showToast('📖 Tutorial complete! Type /help if you need a refresher.', { color: '#c8b16c', duration: 4000 });
  }
}

export function isTutorialActive() {
  return _active;
}

export default { openTutorial, closeTutorial, advanceTutorial, exitTutorial, isTutorialActive };
