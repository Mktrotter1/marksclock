// World clock page

import { api, $ } from './utils.js';

let refreshInterval;

export async function render(container) {
  container.innerHTML = `
    <h2 class="page-title">World Clock</h2>
    <div class="card">
      <div class="form-row">
        <div class="form-group" style="flex:3">
          <input class="input" id="addTz" placeholder="e.g. Europe/Berlin" list="tzList" />
          <datalist id="tzList"></datalist>
        </div>
        <div class="form-group" style="flex:1">
          <button class="btn btn-primary" id="addTzBtn" style="width:100%">Add</button>
        </div>
      </div>
    </div>
    <div id="worldList" class="grid-2"></div>
  `;

  // Load timezone list for autocomplete
  const tzData = await api('/reference/timezones');
  const dl = $('#tzList');
  for (const tz of tzData) {
    const opt = document.createElement('option');
    opt.value = tz.timezone;
    dl.appendChild(opt);
  }

  $('#addTzBtn').onclick = async () => {
    const tz = $('#addTz').value.trim();
    if (!tz) return;
    await api('/worldclock', { method: 'POST', body: { timezone: tz } });
    $('#addTz').value = '';
    await refresh();
  };

  await refresh();
  refreshInterval = setInterval(refresh, 1000);
}

async function refresh() {
  const zones = await api('/worldclock');
  const list = $('#worldList');
  if (!list) return;

  list.innerHTML = '';
  for (const z of zones) {
    list.innerHTML += `
      <div class="card">
        <div class="flex-between mb-1">
          <span class="text-secondary" style="font-size:0.8rem">${z.timezone}</span>
          <button class="btn btn-icon zone-del" data-tz="${z.timezone}">&times;</button>
        </div>
        <div class="time-display-sm">${z.time_12h}</div>
        <div class="text-dim" style="font-size:0.8rem">${z.day_of_week}, ${z.date} &middot; ${z.abbreviation} (${z.utc_offset})</div>
      </div>
    `;
  }

  list.querySelectorAll('.zone-del').forEach(b => {
    b.onclick = () => api(`/worldclock/${b.dataset.tz}`, { method: 'DELETE' }).then(refresh);
  });
}

export function destroy() {
  if (refreshInterval) clearInterval(refreshInterval);
}
