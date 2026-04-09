// Stopwatch page

import { api, formatDuration, $ } from './utils.js';

let refreshInterval;

export async function render(container) {
  container.innerHTML = `
    <h2 class="page-title">Stopwatch</h2>
    <div class="card text-center">
      <div class="time-display" id="swDisplay">00:00.00</div>
      <div class="flex-center gap-1 mt-2">
        <button class="btn btn-primary" id="swStart">Start</button>
        <button class="btn btn-ghost" id="swLap">Lap</button>
        <button class="btn btn-ghost" id="swStop">Stop</button>
        <button class="btn btn-danger" id="swReset">Reset</button>
      </div>
    </div>
    <div class="card" id="lapCard" style="display:none">
      <h3 class="card-title mb-1">Laps</h3>
      <table>
        <thead><tr><th>#</th><th>Time</th><th>Split</th></tr></thead>
        <tbody id="lapBody"></tbody>
      </table>
    </div>
  `;

  $('#swStart').onclick = () => api('/stopwatch/start', { method: 'POST' }).then(refresh);
  $('#swStop').onclick = () => api('/stopwatch/stop', { method: 'POST' }).then(refresh);
  $('#swLap').onclick = () => api('/stopwatch/lap', { method: 'POST' }).then(refresh);
  $('#swReset').onclick = () => api('/stopwatch/reset', { method: 'POST' }).then(refresh);

  await refresh();
  refreshInterval = setInterval(refresh, 50);
}

async function refresh() {
  const data = await api('/stopwatch');
  const disp = $('#swDisplay');
  if (disp) disp.textContent = formatDuration(data.elapsed);

  if (data.laps && data.laps.length > 0) {
    const card = $('#lapCard');
    if (card) card.style.display = '';
    const body = $('#lapBody');
    if (body) {
      body.innerHTML = '';
      for (let i = data.laps.length - 1; i >= 0; i--) {
        const split = i === 0 ? data.laps[0] : data.laps[i] - data.laps[i - 1];
        body.innerHTML += `<tr><td>${i + 1}</td><td>${formatDuration(data.laps[i])}</td><td>${formatDuration(split)}</td></tr>`;
      }
    }
  }
}

export function destroy() {
  if (refreshInterval) clearInterval(refreshInterval);
}
