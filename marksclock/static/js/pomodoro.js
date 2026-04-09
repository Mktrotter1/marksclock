// Pomodoro timer page

import { api, formatTimer, $ } from './utils.js';

let refreshInterval;

const PHASE_LABELS = {
  idle: 'Ready',
  work: 'Work',
  short_break: 'Short Break',
  long_break: 'Long Break',
};

const PHASE_COLORS = {
  idle: 'var(--dim)',
  work: 'var(--danger)',
  short_break: 'var(--success)',
  long_break: 'var(--primary)',
};

export async function render(container) {
  container.innerHTML = `
    <h2 class="page-title">Pomodoro</h2>
    <div class="card text-center">
      <div class="mb-1">
        <span class="badge" id="pomPhase">Ready</span>
      </div>
      <div class="pomodoro-circle">
        <canvas id="pomCanvas" width="200" height="200"></canvas>
      </div>
      <div class="time-display" id="pomTime">00:00</div>
      <div class="text-secondary mt-1" id="pomSessions">0 sessions completed</div>
      <div class="flex-center gap-1 mt-2">
        <button class="btn btn-primary" id="pomStart">Start</button>
        <button class="btn btn-ghost" id="pomPause">Pause</button>
        <button class="btn btn-ghost" id="pomSkip">Skip</button>
        <button class="btn btn-danger" id="pomReset">Reset</button>
      </div>
    </div>
    <div class="card">
      <h3 class="card-title mb-1">Settings</h3>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Work (min)</label>
          <input class="input" id="pomWork" type="number" value="25" min="1" />
        </div>
        <div class="form-group">
          <label class="form-label">Short break</label>
          <input class="input" id="pomShort" type="number" value="5" min="1" />
        </div>
        <div class="form-group">
          <label class="form-label">Long break</label>
          <input class="input" id="pomLong" type="number" value="15" min="1" />
        </div>
      </div>
      <button class="btn btn-ghost" id="pomSave">Save Settings</button>
    </div>
  `;

  $('#pomStart').onclick = () => api('/pomodoro/start', { method: 'POST' }).then(refresh);
  $('#pomPause').onclick = () => api('/pomodoro/pause', { method: 'POST' }).then(refresh);
  $('#pomSkip').onclick = () => api('/pomodoro/skip', { method: 'POST' }).then(refresh);
  $('#pomReset').onclick = () => api('/pomodoro/reset', { method: 'POST' }).then(refresh);
  $('#pomSave').onclick = async () => {
    await api('/pomodoro/config', {
      method: 'PUT',
      body: {
        work_minutes: parseInt($('#pomWork').value),
        short_break_minutes: parseInt($('#pomShort').value),
        long_break_minutes: parseInt($('#pomLong').value),
        sessions_before_long: 4,
      },
    });
  };

  // Load config
  const cfg = await api('/pomodoro/config');
  $('#pomWork').value = cfg.work_minutes;
  $('#pomShort').value = cfg.short_break_minutes;
  $('#pomLong').value = cfg.long_break_minutes;

  await refresh();
  refreshInterval = setInterval(refresh, 1000);
}

async function refresh() {
  const data = await api('/pomodoro');
  const time = $('#pomTime');
  if (time) time.textContent = formatTimer(data.remaining);

  const phase = $('#pomPhase');
  if (phase) {
    phase.textContent = PHASE_LABELS[data.phase] || data.phase;
    phase.style.background = PHASE_COLORS[data.phase] || 'var(--dim)';
    phase.style.color = '#fff';
    phase.style.padding = '0.25rem 0.75rem';
  }

  const sess = $('#pomSessions');
  if (sess) sess.textContent = `${data.completed_sessions} sessions completed`;

  // Draw circle
  const canvas = $('#pomCanvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    const size = 200;
    const center = size / 2;
    const r = 85;
    ctx.clearRect(0, 0, size, size);

    // Background circle
    ctx.beginPath();
    ctx.arc(center, center, r, 0, Math.PI * 2);
    ctx.strokeStyle = 'var(--border)';
    ctx.lineWidth = 8;
    ctx.stroke();

    // Progress arc
    if (data.phase !== 'idle') {
      const totalSec = {
        work: data.work_minutes * 60,
        short_break: data.short_break_minutes * 60,
        long_break: (data.long_break_minutes || 15) * 60,
      }[data.phase] || 1;
      const pct = 1 - data.remaining / totalSec;
      ctx.beginPath();
      ctx.arc(center, center, r, -Math.PI / 2, -Math.PI / 2 + pct * Math.PI * 2);
      ctx.strokeStyle = PHASE_COLORS[data.phase] || '#3b82f6';
      ctx.lineWidth = 8;
      ctx.lineCap = 'round';
      ctx.stroke();
    }
  }
}

export function destroy() {
  if (refreshInterval) clearInterval(refreshInterval);
}
