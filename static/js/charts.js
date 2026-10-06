const style = getComputedStyle(document.documentElement);
const v = (name) => style.getPropertyValue(name).trim();
const seriesColors = [v('--series-1'), v('--series-2'), v('--series-3'), v('--series-4'), v('--series-5')];

Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', sans-serif";
Chart.defaults.color = v('--text-secondary');
Chart.defaults.borderColor = v('--gridline');

// Draws a multi-series line chart (used for "hours per month, by X" on every dashboard).
function lineChart(canvasId, labels, series, yLabel) {
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
    },
  });
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
