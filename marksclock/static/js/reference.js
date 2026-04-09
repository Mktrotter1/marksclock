// Timezone reference page

import { api, $ } from './utils.js';

export async function render(container) {
  container.innerHTML = `
    <h2 class="page-title">Timezone Reference</h2>
    <div class="card">
      <div class="form-row">
        <div class="form-group" style="flex:3">
          <input class="input" id="tzFilter" placeholder="Filter timezones..." />
        </div>
        <div class="form-group" style="flex:2">
          <input class="input" id="dstZone" placeholder="Check DST for zone..." list="tzRef" />
        </div>
        <div class="form-group" style="flex:1">
          <button class="btn btn-ghost" id="dstCheck" style="width:100%">DST Info</button>
        </div>
      </div>
    </div>
    <div id="dstResult" class="mb-2"></div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Timezone</th><th>Abbr</th><th>UTC Offset</th></tr></thead>
          <tbody id="tzBody"></tbody>
        </table>
      </div>
    </div>
    <datalist id="tzRef"></datalist>
  `;

  let allTz = [];

  async function loadTimezones(filter) {
    const q = filter ? `?filter=${encodeURIComponent(filter)}` : '';
    allTz = await api(`/reference/timezones${q}`);
    renderTable();
  }

  function renderTable() {
    const body = $('#tzBody');
    if (!body) return;
    body.innerHTML = allTz.slice(0, 200).map(tz =>
      `<tr><td class="mono" style="font-size:0.8rem">${tz.timezone}</td><td>${tz.abbreviation}</td><td class="mono">${tz.utc_offset} (${tz.utc_offset_hours >= 0 ? '+' : ''}${tz.utc_offset_hours}h)</td></tr>`
    ).join('');

    // Populate datalist
    const dl = $('#tzRef');
    dl.innerHTML = '';
    for (const tz of allTz) {
      const opt = document.createElement('option');
      opt.value = tz.timezone;
      dl.appendChild(opt);
    }
  }

  let debounce;
  $('#tzFilter').oninput = (e) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => loadTimezones(e.target.value), 300);
  };

  $('#dstCheck').onclick = async () => {
    const zone = $('#dstZone').value.trim();
    if (!zone) return;
    const r = await api(`/reference/dst/${zone}`);
    const res = $('#dstResult');
    if (!r.transitions || r.transitions.length === 0) {
      res.innerHTML = `<div class="card"><span class="badge badge-primary">No DST</span> ${zone} does not observe Daylight Saving Time in ${r.year}.</div>`;
    } else {
      res.innerHTML = `<div class="card">
        <span class="badge badge-warning">DST Active</span> ${zone} in ${r.year}:
        <table class="mt-1"><thead><tr><th>Date</th><th>Change</th></tr></thead><tbody>
        ${r.transitions.map(t => `<tr><td>${t.date}</td><td>${t.from_offset} &rarr; ${t.to_offset}</td></tr>`).join('')}
        </tbody></table></div>`;
    }
  };

  await loadTimezones();
}

export function destroy() {}
