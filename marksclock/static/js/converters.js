// Converters / calculators page

import { api, $ } from './utils.js';

export async function render(container) {
  container.innerHTML = `
    <h2 class="page-title">Time Tools</h2>

    <div class="card">
      <h3 class="card-title mb-1">Timezone Converter</h3>
      <div class="form-row">
        <div class="form-group"><label class="form-label">Date/Time</label><input class="input" id="tzTime" type="datetime-local" /></div>
        <div class="form-group"><label class="form-label">From</label><input class="input" id="tzFrom" value="America/New_York" list="tzList1" /></div>
        <div class="form-group"><label class="form-label">To</label><input class="input" id="tzTo" value="Europe/London" list="tzList1" /></div>
      </div>
      <button class="btn btn-primary" id="tzConvert">Convert</button>
      <div id="tzResult" class="mt-1 mono"></div>
      <datalist id="tzList1"></datalist>
    </div>

    <div class="card">
      <h3 class="card-title mb-1">Unix Timestamp</h3>
      <div class="form-row">
        <div class="form-group"><label class="form-label">Timestamp</label><input class="input" id="unixTs" type="number" placeholder="e.g. 1700000000" /></div>
        <div class="form-group"><label class="form-label">Or ISO string</label><input class="input" id="unixIso" placeholder="2024-01-01T00:00:00Z" /></div>
      </div>
      <button class="btn btn-primary" id="unixConvert">Convert</button>
      <div id="unixResult" class="mt-1 mono"></div>
    </div>

    <div class="card">
      <h3 class="card-title mb-1">Time Difference</h3>
      <div class="form-row">
        <div class="form-group"><label class="form-label">Start</label><input class="input" id="diffStart" type="datetime-local" /></div>
        <div class="form-group"><label class="form-label">End</label><input class="input" id="diffEnd" type="datetime-local" /></div>
      </div>
      <button class="btn btn-primary" id="diffCalc">Calculate</button>
      <div id="diffResult" class="mt-1 mono"></div>
    </div>

    <div class="card">
      <h3 class="card-title mb-1">Date Add/Subtract</h3>
      <div class="form-row">
        <div class="form-group"><label class="form-label">Start Date</label><input class="input" id="addDate" type="date" /></div>
        <div class="form-group"><label class="form-label">Years</label><input class="input" id="addY" type="number" value="0" /></div>
        <div class="form-group"><label class="form-label">Months</label><input class="input" id="addM" type="number" value="0" /></div>
        <div class="form-group"><label class="form-label">Days</label><input class="input" id="addD" type="number" value="0" /></div>
      </div>
      <button class="btn btn-primary" id="addCalc">Calculate</button>
      <div id="addResult" class="mt-1 mono"></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <h3 class="card-title mb-1">Age Calculator</h3>
        <div class="form-group"><label class="form-label">Birthdate</label><input class="input" id="ageBirth" type="date" /></div>
        <button class="btn btn-primary" id="ageCalc">Calculate</button>
        <div id="ageResult" class="mt-1 mono"></div>
      </div>

      <div class="card">
        <h3 class="card-title mb-1">Days Between</h3>
        <div class="form-group"><label class="form-label">Start</label><input class="input" id="betStart" type="date" /></div>
        <div class="form-group"><label class="form-label">End</label><input class="input" id="betEnd" type="date" /></div>
        <button class="btn btn-primary" id="betCalc">Calculate</button>
        <div id="betResult" class="mt-1 mono"></div>
      </div>

      <div class="card">
        <h3 class="card-title mb-1">Leap Year</h3>
        <div class="form-group"><label class="form-label">Year</label><input class="input" id="leapYear" type="number" value="${new Date().getFullYear()}" /></div>
        <button class="btn btn-primary" id="leapCalc">Check</button>
        <div id="leapResult" class="mt-1 mono"></div>
      </div>

      <div class="card">
        <h3 class="card-title mb-1">Day of Week</h3>
        <div class="form-group"><label class="form-label">Date</label><input class="input" id="dowDate" type="date" /></div>
        <button class="btn btn-primary" id="dowCalc">Check</button>
        <div id="dowResult" class="mt-1 mono"></div>
      </div>
    </div>
  `;

  // Load timezone list
  const tzData = await api('/reference/timezones');
  const dl = $('#tzList1');
  for (const tz of tzData) {
    const opt = document.createElement('option');
    opt.value = tz.timezone;
    dl.appendChild(opt);
  }

  // Set defaults
  const now = new Date();
  const localIso = now.toISOString().slice(0, 16);
  $('#tzTime').value = localIso;
  $('#diffStart').value = localIso;
  $('#diffEnd').value = localIso;
  $('#addDate').value = now.toISOString().slice(0, 10);
  $('#ageBirth').value = '1990-01-01';
  $('#betStart').value = now.toISOString().slice(0, 10);
  $('#betEnd').value = now.toISOString().slice(0, 10);
  $('#dowDate').value = now.toISOString().slice(0, 10);

  // Timezone convert
  $('#tzConvert').onclick = async () => {
    const r = await api('/convert/timezone', { method: 'POST', body: { time_iso: $('#tzTime').value, from_tz: $('#tzFrom').value, to_tz: $('#tzTo').value } });
    $('#tzResult').textContent = r.to ? `${r.to.time}` : JSON.stringify(r);
  };

  // Unix
  $('#unixConvert').onclick = async () => {
    const ts = $('#unixTs').value;
    const iso = $('#unixIso').value;
    const body = ts ? { timestamp: parseFloat(ts) } : { iso };
    const r = await api('/convert/unix', { method: 'POST', body });
    $('#unixResult').innerHTML = `Epoch: ${r.timestamp}<br>ISO: ${r.iso}<br>${r.human}`;
  };

  // Duration
  $('#diffCalc').onclick = async () => {
    const r = await api('/convert/duration', { method: 'POST', body: { start: $('#diffStart').value, end: $('#diffEnd').value } });
    $('#diffResult').textContent = r.human || JSON.stringify(r);
  };

  // Date add
  $('#addCalc').onclick = async () => {
    const r = await api('/convert/date-add', { method: 'POST', body: { date: $('#addDate').value, years: parseInt($('#addY').value), months: parseInt($('#addM').value), days: parseInt($('#addD').value) } });
    $('#addResult').textContent = r.result || JSON.stringify(r);
  };

  // Age
  $('#ageCalc').onclick = async () => {
    const r = await api(`/convert/age?birthdate=${$('#ageBirth').value}`);
    $('#ageResult').textContent = r.human || JSON.stringify(r);
  };

  // Days between
  $('#betCalc').onclick = async () => {
    const r = await api(`/convert/days-between?start=${$('#betStart').value}&end=${$('#betEnd').value}`);
    $('#betResult').textContent = `${r.days} days (${(r.weeks || 0).toFixed(1)} weeks)`;
  };

  // Leap year
  $('#leapCalc').onclick = async () => {
    const r = await api(`/convert/leap-year?year=${$('#leapYear').value}`);
    $('#leapResult').textContent = r.is_leap_year ? 'Yes, leap year' : 'No, not a leap year';
  };

  // Day of week
  $('#dowCalc').onclick = async () => {
    const r = await api(`/convert/day-of-week?date=${$('#dowDate').value}`);
    $('#dowResult').textContent = r.day_of_week || JSON.stringify(r);
  };
}

export function destroy() {}
