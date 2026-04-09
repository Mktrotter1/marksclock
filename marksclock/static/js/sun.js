// Sunrise/sunset page

import { api, $ } from './utils.js';

export async function render(container) {
  container.innerHTML = `
    <h2 class="page-title">Sunrise / Sunset</h2>
    <div class="card">
      <div class="form-row">
        <div class="form-group"><label class="form-label">Latitude</label><input class="input" id="sunLat" type="number" step="0.001" placeholder="e.g. 40.7128" /></div>
        <div class="form-group"><label class="form-label">Longitude</label><input class="input" id="sunLon" type="number" step="0.001" placeholder="e.g. -74.0060" /></div>
        <div class="form-group"><label class="form-label">Date</label><input class="input" id="sunDate" type="date" /></div>
      </div>
      <div class="flex gap-1">
        <button class="btn btn-primary" id="sunCalc">Calculate</button>
        <button class="btn btn-ghost" id="sunGeo">Use My Location</button>
      </div>
    </div>
    <div id="sunResult" class="grid-3"></div>
  `;

  $('#sunDate').value = new Date().toISOString().slice(0, 10);

  $('#sunGeo').onclick = () => {
    navigator.geolocation.getCurrentPosition(pos => {
      $('#sunLat').value = pos.coords.latitude.toFixed(4);
      $('#sunLon').value = pos.coords.longitude.toFixed(4);
    });
  };

  $('#sunCalc').onclick = async () => {
    const lat = $('#sunLat').value;
    const lon = $('#sunLon').value;
    const date = $('#sunDate').value;
    if (!lat || !lon) return;

    const r = await api(`/sun?lat=${lat}&lon=${lon}&date_str=${date}`);
    if (r.error) {
      $('#sunResult').innerHTML = `<div class="card text-danger">${r.error}</div>`;
      return;
    }

    const fmt = iso => new Date(iso).toLocaleTimeString();
    $('#sunResult').innerHTML = `
      <div class="card text-center">
        <div class="text-dim" style="font-size:2rem">&#127749;</div>
        <div class="form-label">Dawn</div>
        <div class="mono">${fmt(r.dawn)}</div>
      </div>
      <div class="card text-center">
        <div class="text-dim" style="font-size:2rem">&#127773;</div>
        <div class="form-label">Sunrise</div>
        <div class="mono">${fmt(r.sunrise)}</div>
      </div>
      <div class="card text-center">
        <div class="text-dim" style="font-size:2rem">&#9728;</div>
        <div class="form-label">Solar Noon</div>
        <div class="mono">${fmt(r.noon)}</div>
      </div>
      <div class="card text-center">
        <div class="text-dim" style="font-size:2rem">&#127751;</div>
        <div class="form-label">Sunset</div>
        <div class="mono">${fmt(r.sunset)}</div>
      </div>
      <div class="card text-center">
        <div class="text-dim" style="font-size:2rem">&#127753;</div>
        <div class="form-label">Dusk</div>
        <div class="mono">${fmt(r.dusk)}</div>
      </div>
      <div class="card text-center">
        <div class="text-dim" style="font-size:2rem">&#128336;</div>
        <div class="form-label">Day Length</div>
        <div class="mono">${r.day_length_hours}h</div>
      </div>
    `;
  };
}

export function destroy() {}
