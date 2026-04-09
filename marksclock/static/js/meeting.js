// Meeting planner page

import { api, $ } from './utils.js';

export async function render(container) {
  container.innerHTML = `
    <h2 class="page-title">Meeting Planner</h2>
    <div class="card">
      <p class="text-secondary mb-1">Find overlapping business hours across timezones.</p>
      <div class="form-group">
        <label class="form-label">Timezones (one per line)</label>
        <textarea class="input" id="meetZones" rows="4" style="resize:vertical" placeholder="America/New_York\nEurope/London\nAsia/Tokyo"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group"><label class="form-label">Work Start</label><input class="input" id="meetStart" type="time" value="09:00" /></div>
        <div class="form-group"><label class="form-label">Work End</label><input class="input" id="meetEnd" type="time" value="17:00" /></div>
      </div>
      <button class="btn btn-primary" id="meetCalc">Find Overlap</button>
    </div>
    <div id="meetResult"></div>
  `;

  $('#meetCalc').onclick = async () => {
    const zones = $('#meetZones').value.trim().split('\n').map(s => s.trim()).filter(Boolean);
    if (zones.length < 2) return;

    const r = await api('/meeting/overlap', {
      method: 'POST',
      body: { timezones: zones, work_start: $('#meetStart').value, work_end: $('#meetEnd').value },
    });

    const res = $('#meetResult');
    if (!r.overlap) {
      res.innerHTML = `<div class="card"><span class="badge badge-danger">No Overlap</span> ${r.message}</div>`;
    } else {
      res.innerHTML = `
        <div class="card">
          <span class="badge badge-success">${r.overlap_hours}h Overlap</span>
          <div class="mt-1 mono">${r.overlap_utc_start} - ${r.overlap_utc_end}</div>
          <table class="mt-1">
            <thead><tr><th>Timezone</th><th>Local Start</th><th>Local End</th></tr></thead>
            <tbody>
              ${r.per_zone.map(z => `<tr><td>${z.timezone}</td><td class="mono">${z.overlap_start}</td><td class="mono">${z.overlap_end}</td></tr>`).join('')}
            </tbody>
          </table>
        </div>
      `;
    }
  };
}

export function destroy() {}
