// Alarms page

import { api, $ } from './utils.js';

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export async function render(container) {
  container.innerHTML = `
    <h2 class="page-title">Alarms</h2>
    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Label</label>
          <input class="input" id="alarmLabel" value="Alarm" />
        </div>
        <div class="form-group">
          <label class="form-label">Time</label>
          <input class="input" id="alarmTime" type="time" value="07:00" />
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Recurring</label>
        <div class="flex gap-1" id="dayButtons">
          ${DAY_NAMES.map((d, i) => `<button class="btn btn-ghost day-btn" data-day="${i}">${d}</button>`).join('')}
        </div>
      </div>
      <button class="btn btn-primary" id="addAlarm">Add Alarm</button>
    </div>
    <div id="alarmList"></div>
  `;

  const selectedDays = new Set();
  container.querySelectorAll('.day-btn').forEach(b => {
    b.onclick = () => {
      const day = parseInt(b.dataset.day);
      if (selectedDays.has(day)) {
        selectedDays.delete(day);
        b.classList.remove('btn-primary');
        b.classList.add('btn-ghost');
      } else {
        selectedDays.add(day);
        b.classList.remove('btn-ghost');
        b.classList.add('btn-primary');
      }
    };
  });

  $('#addAlarm').onclick = async () => {
    const label = $('#alarmLabel').value;
    const time_str = $('#alarmTime').value;
    const days = [...selectedDays];
    await api('/alarms', { method: 'POST', body: { label, time_str, recurring: days.length > 0, days } });
    await refreshList();
  };

  await refreshList();
}

async function refreshList() {
  const alarms = await api('/alarms');
  const list = $('#alarmList');
  if (!list) return;

  list.innerHTML = '';
  for (const a of alarms) {
    const daysStr = a.recurring ? a.days.map(d => DAY_NAMES[d]).join(', ') : 'One-time';
    list.innerHTML += `
      <div class="card flex-between">
        <div>
          <div class="time-display-sm">${a.time}</div>
          <div class="text-secondary">${a.label} &middot; ${daysStr}</div>
        </div>
        <div class="flex gap-1">
          <label class="toggle">
            <input type="checkbox" ${a.enabled ? 'checked' : ''} data-id="${a.id}" class="alarm-toggle" />
            <span class="toggle-slider"></span>
          </label>
          <button class="btn btn-icon alarm-del" data-id="${a.id}">&times;</button>
        </div>
      </div>
    `;
  }

  list.querySelectorAll('.alarm-toggle').forEach(t => {
    t.onchange = () => api(`/alarms/${t.dataset.id}`, { method: 'PATCH' }).then(refreshList);
  });
  list.querySelectorAll('.alarm-del').forEach(b => {
    b.onclick = () => api(`/alarms/${b.dataset.id}`, { method: 'DELETE' }).then(refreshList);
  });
}

export function destroy() {}
