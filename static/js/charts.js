const style = getComputedStyle(document.documentElement);
const v = (name) => style.getPropertyValue(name).trim();
const seriesColors = [v('--series-1'), v('--series-2'), v('--series-3'), v('--series-4'), v('--series-5')];

Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', sans-serif";
Chart.defaults.color = v('--text-secondary');
Chart.defaults.borderColor = v('--gridline');

// Draws a multi-series line chart (used for "hours per month, by X" on every dashboard).
// titlesByMonth, if given, is {month: [{title, date, hours, service}, ...]} - clicking a
// point opens a dialog listing everything watched that month. monthSpend/currency, if given,
// show a combined spend total for that month in the dialog (for the multi-service overview).
function lineChart(canvasId, labels, series, yLabel, titlesByMonth, monthSpend, currency) {
  return new Chart(document.getElementById(canvasId), {
    type: 'line',
    data: {
      labels,
      datasets: Object.entries(series).map(([name, data], i) => ({
        label: name,
        data,
        borderColor: seriesColors[i % seriesColors.length],
        backgroundColor: seriesColors[i % seriesColors.length],
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.15,
      })),
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: { y: { beginAtZero: true, title: { display: !!yLabel, text: yLabel } } },
      onClick: titlesByMonth ? (evt, _els, chart) => {
        const points = chart.getElementsAtEventForMode(evt, 'index', { intersect: false }, true);
        if (points.length) showMonthDialog(labels[points[0].index], titlesByMonth, monthSpend, currency);
      } : undefined,
    },
  });
}

// Opens a <dialog> listing every title watched in `month` (from titlesByMonth, keyed "YYYY-MM"),
// sorted by service then by watched length (longest first).
function showMonthDialog(month, titlesByMonth, monthSpend, currency) {
  const items = (titlesByMonth[month] || []).slice()
    .sort((a, b) => a.service.localeCompare(b.service) || b.hours - a.hours);
  let dialog = document.getElementById('month-dialog');
  if (!dialog) {
    dialog = document.createElement('dialog');
    dialog.id = 'month-dialog';
    dialog.className = 'card';
    dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });
    document.body.appendChild(dialog);
  }
  const spend = monthSpend && monthSpend[month];
  const rows = items.map((i) => `<tr><td>${i.title}</td><td>${i.service}</td><td>${i.date}</td><td class="num">${i.hours}</td></tr>`).join('');
  dialog.innerHTML = `
    <form method="dialog">
      <h2>${month}</h2>
      ${spend ? `<p class="empty">Total spent this month: ${spend} ${currency}</p>` : ''}
      ${items.length
        ? `<div class="table-wrap"><table class="watch-table"><thead><tr><th>Title</th><th>Service</th><th>Date</th><th class="num">Hours</th></tr></thead><tbody>${rows}</tbody></table></div>`
        : '<p class="empty">Nothing watched this month.</p>'}
      <button class="btn" autofocus>Close</button>
    </form>`;
  dialog.showModal();
}

// Draws a horizontal bar chart from [label, value] pairs (used for "most-watched titles").
function hbarChart(canvasId, pairs, xLabel) {
  return new Chart(document.getElementById(canvasId), {
    type: 'bar',
    data: {
      labels: pairs.map(([label]) => label),
      datasets: [{
        data: pairs.map(([, value]) => value),
        backgroundColor: seriesColors[0],
        borderRadius: 4,
        maxBarThickness: 24,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, title: { display: !!xLabel, text: xLabel } } },
    },
  });
}

// Makes a <table id="tableId"> searchable (by its first column) and sortable (click any header).
function wireTable(tableId, searchId, countId) {
  const table = document.getElementById(tableId);
  const tbody = table.tBodies[0];
  const rows = Array.from(tbody.rows);
  const search = document.getElementById(searchId);
  const count = countId && document.getElementById(countId);

  function updateCount(visible) {
    if (count) count.textContent = `${visible} / ${rows.length}`;
  }
  updateCount(rows.length);

  if (search) {
    search.addEventListener('input', () => {
      const q = search.value.toLowerCase();
      let visible = 0;
      for (const row of rows) {
        const match = row.cells[0].textContent.toLowerCase().includes(q);
        row.style.display = match ? '' : 'none';
        if (match) visible++;
      }
      updateCount(visible);
    });
  }

  const headers = Array.from(table.tHead.rows[0].cells);
  let sort = { col: null, dir: 1 };
  headers.forEach((th, col) => {
    th.addEventListener('click', () => {
      sort = { col, dir: sort.col === col ? -sort.dir : 1 };
      const numeric = th.classList.contains('num');
      rows.sort((a, b) => {
        let av = a.cells[col].textContent.trim();
        let bv = b.cells[col].textContent.trim();
        if (numeric) { av = parseFloat(av) || 0; bv = parseFloat(bv) || 0; }
        return av < bv ? -sort.dir : av > bv ? sort.dir : 0;
      });
      rows.forEach((r) => tbody.appendChild(r));
      headers.forEach((h) => { const a = h.querySelector('.sort-arrow'); if (a) a.remove(); });
      const arrow = document.createElement('span');
      arrow.className = 'sort-arrow';
      arrow.textContent = sort.dir === 1 ? ' ▲' : ' ▼';
      th.appendChild(arrow);
    });
  });
}
