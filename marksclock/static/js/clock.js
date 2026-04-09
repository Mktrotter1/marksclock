// Clock page — digital + analog display

import { $, el } from './utils.js';

let canvas, ctx, animFrame;
let currentTime = new Date();

export function render(container) {
  container.innerHTML = `
    <div class="clock-page">
      <div class="time-display" id="digitalClock">--:--:--</div>
      <div class="date-display" id="dateDisplay">---</div>
      <div class="analog-clock">
        <canvas id="analogClock" width="300" height="300"></canvas>
      </div>
      <div class="clock-formats" id="clockFormats"></div>
    </div>
  `;
  canvas = $('#analogClock');
  ctx = canvas.getContext('2d');
  update();
}

export function onTick(data) {
  currentTime = new Date(data.utc_iso);
  update();
}

function update() {
  const now = currentTime;
  const h = now.getHours();
  const m = now.getMinutes();
  const s = now.getSeconds();

  // Digital
  const dig = $(`#digitalClock`);
  if (dig) {
    const h12 = h % 12 || 12;
    const ampm = h < 12 ? 'AM' : 'PM';
    dig.textContent = `${String(h12).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')} ${ampm}`;
  }

  // Date
  const dd = $('#dateDisplay');
  if (dd) {
    dd.textContent = now.toLocaleDateString(undefined, {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
  }

  // Format cards
  const fmt = $('#clockFormats');
  if (fmt) {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const offset = now.getTimezoneOffset();
    const offsetH = Math.floor(Math.abs(offset) / 60);
    const offsetM = Math.abs(offset) % 60;
    const offsetStr = `${offset <= 0 ? '+' : '-'}${String(offsetH).padStart(2,'0')}:${String(offsetM).padStart(2,'0')}`;
    const isoWeek = getISOWeek(now);
    const epoch = Math.floor(now.getTime() / 1000);

    fmt.innerHTML = `
      <div class="clock-format-card">
        <div class="clock-format-label">24-Hour</div>
        <div class="clock-format-value">${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}</div>
      </div>
      <div class="clock-format-card">
        <div class="clock-format-label">Timezone</div>
        <div class="clock-format-value">${tz}</div>
      </div>
      <div class="clock-format-card">
        <div class="clock-format-label">UTC Offset</div>
        <div class="clock-format-value">${offsetStr}</div>
      </div>
      <div class="clock-format-card">
        <div class="clock-format-label">ISO 8601</div>
        <div class="clock-format-value" style="font-size:0.75rem">${now.toISOString()}</div>
      </div>
      <div class="clock-format-card">
        <div class="clock-format-label">Unix Epoch</div>
        <div class="clock-format-value">${epoch}</div>
      </div>
      <div class="clock-format-card">
        <div class="clock-format-label">ISO Week</div>
        <div class="clock-format-value">W${isoWeek}</div>
      </div>
    `;
  }

  drawAnalog(now);
}

function drawAnalog(now) {
  if (!ctx) return;
  const size = 300;
  const center = size / 2;
  const r = center - 10;

  ctx.clearRect(0, 0, size, size);

  // Face
  ctx.beginPath();
  ctx.arc(center, center, r, 0, Math.PI * 2);
  ctx.fillStyle = '#1a1a2e';
  ctx.fill();
  ctx.strokeStyle = '#2a2a45';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Hour marks
  for (let i = 0; i < 12; i++) {
    const angle = (i * Math.PI) / 6 - Math.PI / 2;
    const inner = i % 3 === 0 ? r - 20 : r - 12;
    ctx.beginPath();
    ctx.moveTo(center + inner * Math.cos(angle), center + inner * Math.sin(angle));
    ctx.lineTo(center + (r - 4) * Math.cos(angle), center + (r - 4) * Math.sin(angle));
    ctx.strokeStyle = i % 3 === 0 ? '#eeeeee' : '#666666';
    ctx.lineWidth = i % 3 === 0 ? 2.5 : 1.5;
    ctx.stroke();
  }

  // Minute marks
  for (let i = 0; i < 60; i++) {
    if (i % 5 === 0) continue;
    const angle = (i * Math.PI) / 30 - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(center + (r - 6) * Math.cos(angle), center + (r - 6) * Math.sin(angle));
    ctx.lineTo(center + (r - 3) * Math.cos(angle), center + (r - 3) * Math.sin(angle));
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  const h = now.getHours() % 12;
  const m = now.getMinutes();
  const s = now.getSeconds();

  // Hour hand
  drawHand(center, (h + m / 60) * (Math.PI / 6) - Math.PI / 2, r * 0.5, 4, '#eeeeee');
  // Minute hand
  drawHand(center, (m + s / 60) * (Math.PI / 30) - Math.PI / 2, r * 0.7, 2.5, '#aaaaaa');
  // Second hand
  drawHand(center, s * (Math.PI / 30) - Math.PI / 2, r * 0.8, 1, '#3b82f6');

  // Center dot
  ctx.beginPath();
  ctx.arc(center, center, 4, 0, Math.PI * 2);
  ctx.fillStyle = '#3b82f6';
  ctx.fill();
}

function drawHand(center, angle, length, width, color) {
  ctx.beginPath();
  ctx.moveTo(center, center);
  ctx.lineTo(center + length * Math.cos(angle), center + length * Math.sin(angle));
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  ctx.stroke();
}

function getISOWeek(d) {
  const date = new Date(d.getTime());
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() + 3 - (date.getDay() + 6) % 7);
  const week1 = new Date(date.getFullYear(), 0, 4);
  return 1 + Math.round(((date - week1) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7);
}

export function destroy() {
  if (animFrame) cancelAnimationFrame(animFrame);
}
