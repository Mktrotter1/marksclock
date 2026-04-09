// Timers page — countdown timers

import { api, formatTimer, el, $ } from './utils.js';

let refreshInterval;

export async function render(container) {
  container.innerHTML = `
    <h2 class="page-title">Timers</h2>
    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Label</label>
          <input class="input" id="timerLabel" value="Timer" />
        </div>
        <div class="form-group">
          <label class="form-label">Hours</label>
          <input class="input" id="timerH" type="number" value="0" min="0" />
        </div>
        <div class="form-group">
          <label class="form-label">Minutes</label>
          <input class="input" id="timerM" type="number" value="5" min="0" max="59" />
        </div>
        <div class="form-group">
          <label class="form-label">Seconds</label>
          <input class="input" id="timerS" type="number" value="0" min="0" max="59" />
        </div>
      </div>
      <button class="btn btn-primary" id="addTimer">Add Timer</button>
      <div class="flex gap-1 mt-1">
        <button class="btn btn-ghost preset" data-s="60">1m</button>
        <button class="btn btn-ghost preset" data-s="300">5m</button>
        <button class="btn btn-ghost preset" data-s="600">10m</button>
        <button class="btn btn-ghost preset" data-s="900">15m</button>
        <button class="btn btn-ghost preset" data-s="1800">30m</button>
        <button class="btn btn-ghost preset" data-s="3600">1h</button>
      </div>
    </div>
    <div id="timerList" class="grid-2"></div>
  `;

  $('#addTimer').onclick = addTimer;
  container.querySelectorAll('.preset').forEach(b => {
    b.onclick = () => {
      const s = parseInt(b.dataset.s);
      $('#timerH').value = Math.floor(s / 3600);
      $('#timerM').value = Math.floor((s % 3600) / 60);
      $('#timerS').value = s % 60;
      addTimer();
    };
  });

  await refreshList();
  refreshInterval = setInterval(refreshList, 1000);
}

async function addTimer() {
  const h = parseInt($('#timerH').value) || 0;
  const m = parseInt($('#timerM').value) || 0;
  const s = parseInt($('#timerS').value) || 0;
  const total = h * 3600 + m * 60 + s;
  if (total <= 0) return;
  await api('/timers', { method: 'POST', body: { label: $('#timerLabel').value, duration_seconds: total } });
  await refreshList();
}

async function refreshList() {
  const timers = await api('/timers');
  const list = $('#timerList');
  if (!list) return;

  list.innerHTML = '';
  for (const t of timers) {
    const pct = t.duration > 0 ? ((t.duration - t.remaining) / t.duration * 100) : 0;
    const card = el('div', { className: 'card' });
    card.innerHTML = `
      <div class="flex-between mb-1">
        <span class="card-title">${t.label}</span>
        <span class="badge ${t.status === 'running' ? 'badge-success' : t.status === 'finished' ? 'badge-danger' : 'badge-primary'}">${t.status}</span>
      </div>
      <div class="time-display-sm text-center mb-1">${formatTimer(t.remaining)}</div>
      <div style="background:var(--bg);border-radius:4px;height:4px;margin-bottom:0.75rem">
        <div style="background:var(--primary);height:100%;border-radius:4px;width:${pct}%;transition:width 1s"></div>
      </div>
      <div class="flex gap-1">
        ${t.status === 'running'
          ? `<button class="btn btn-ghost btn-pause" data-id="${t.id}">Pause</button>`
          : `<button class="btn btn-primary btn-start" data-id="${t.id}">Start</button>`
        }
        <button class="btn btn-ghost btn-reset" data-id="${t.id}">Reset</button>
        <button class="btn btn-danger btn-del" data-id="${t.id}">Delete</button>
      </div>
    `;
    list.appendChild(card);
  }

  list.querySelectorAll('.btn-start').forEach(b => b.onclick = () => api(`/timers/${b.dataset.id}/start`, { method: 'POST' }).then(refreshList));
  list.querySelectorAll('.btn-pause').forEach(b => b.onclick = () => api(`/timers/${b.dataset.id}/pause`, { method: 'POST' }).then(refreshList));
  list.querySelectorAll('.btn-reset').forEach(b => b.onclick = () => api(`/timers/${b.dataset.id}/reset`, { method: 'POST' }).then(refreshList));
  list.querySelectorAll('.btn-del').forEach(b => b.onclick = () => api(`/timers/${b.dataset.id}`, { method: 'DELETE' }).then(refreshList));
}

export function destroy() {
  if (refreshInterval) clearInterval(refreshInterval);
}
