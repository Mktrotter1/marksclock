// Calendar page

import { api, $ } from './utils.js';

let currentYear, currentMonth;

export async function render(container) {
  const now = new Date();
  currentYear = now.getFullYear();
  currentMonth = now.getMonth() + 1;

  container.innerHTML = `
    <h2 class="page-title">Calendar</h2>
    <div class="card">
      <div class="flex-between mb-1">
        <button class="btn btn-ghost" id="calPrev">&larr;</button>
        <span class="card-title" id="calTitle"></span>
        <button class="btn btn-ghost" id="calNext">&rarr;</button>
      </div>
      <div class="table-wrap">
        <table id="calTable">
          <thead>
            <tr><th>Wk</th><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th></tr>
          </thead>
          <tbody id="calBody"></tbody>
        </table>
      </div>
    </div>
  `;

  $('#calPrev').onclick = () => { currentMonth--; if (currentMonth < 1) { currentMonth = 12; currentYear--; } refresh(); };
  $('#calNext').onclick = () => { currentMonth++; if (currentMonth > 12) { currentMonth = 1; currentYear++; } refresh(); };

  await refresh();
}

async function refresh() {
  const data = await api(`/calendar/${currentYear}/${currentMonth}`);
  $('#calTitle').textContent = `${data.month_name} ${data.year}`;

  const body = $('#calBody');
  body.innerHTML = '';
  for (const week of data.weeks) {
    let row = `<tr><td class="text-dim" style="font-size:0.75rem">W${week[0].iso_week}</td>`;
    for (const day of week) {
      const cls = [];
      if (!day.in_month) cls.push('text-dim');
      if (day.is_today) cls.push('text-primary');
      const style = day.is_today ? 'font-weight:700;' : '';
      row += `<td class="${cls.join(' ')}" style="${style}">${day.day}</td>`;
    }
    row += '</tr>';
    body.innerHTML += row;
  }
}

export function destroy() {}
