// marksclock — SPA router and WebSocket manager

import * as clock from './clock.js';
import * as timers from './timers.js';
import * as stopwatch from './stopwatch.js';
import * as alarms from './alarms.js';
import * as worldclock from './worldclock.js';
import * as pomodoro from './pomodoro.js';
import * as calendarPage from './calendar.js';
import * as converters from './converters.js';
import * as sun from './sun.js';
import * as reference from './reference.js';
import * as meeting from './meeting.js';

const pages = {
  clock, timers, stopwatch, alarms, worldclock,
  pomodoro, calendar: calendarPage, converters, sun, reference, meeting,
};

let currentPage = null;
let ws = null;

// --- Router ---

function navigate(hash) {
  const page = (hash || '#clock').replace('#', '');

  // Handle "more" menu toggle
  if (page === 'more') {
    const menu = document.getElementById('moreMenu');
    menu.classList.toggle('open');
    return;
  }

  // Close more menu if open
  document.getElementById('moreMenu')?.classList.remove('open');

  const mod = pages[page];
  if (!mod) return;

  // Destroy current page
  if (currentPage && currentPage.destroy) {
    currentPage.destroy();
  }

  currentPage = mod;

  // Update nav active states
  document.querySelectorAll('.nav-item, .tab').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });

  // Render
  const container = document.getElementById('page-container');
  mod.render(container);
}

// --- WebSocket ---

function connectWs() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'clock_tick' && currentPage === pages.clock) {
      clock.onTick(data);
    }
  };

  ws.onclose = () => {
    setTimeout(connectWs, 2000);
  };

  ws.onerror = () => {
    ws.close();
  };
}

// --- Audio banner ---

function setupAudio() {
  const banner = document.getElementById('audioBanner');
  const btn = document.getElementById('enableAudio');

  // Show banner on first visit
  if (!localStorage.getItem('marksclock_audio')) {
    banner.classList.add('show');
  }

  btn.onclick = () => {
    // Create and play silent audio to unlock
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    ctx.resume();
    localStorage.setItem('marksclock_audio', '1');
    banner.classList.remove('show');
  };
}

// --- More menu close on item click ---

document.querySelectorAll('.more-item').forEach(item => {
  item.onclick = () => {
    document.getElementById('moreMenu')?.classList.remove('open');
  };
});

// --- Init ---

window.addEventListener('hashchange', () => navigate(location.hash));

// Initial route
navigate(location.hash || '#clock');
connectWs();
setupAudio();
