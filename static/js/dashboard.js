const data = JSON.parse(document.getElementById('page-data').textContent);
const { hoursPerMonth, spendPerMonth, costPerHour, topTitles, currency } = data;

lineChart('hoursChart', hoursPerMonth.months, hoursPerMonth.series, 'hours');

if (document.getElementById('spendChart')) {
  new Chart(document.getElementById('spendChart'), {
    type: 'bar',
    data: {
      labels: spendPerMonth.months,
      datasets: [{
        data: spendPerMonth.amounts,
        backgroundColor: seriesColors[0],
        borderRadius: 4,
        maxBarThickness: 24,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  new Chart(document.getElementById('costPerHourChart'), {
    type: 'line',
    data: {
      labels: costPerHour.months,
      datasets: [{
        label: 'Cost per hour',
        data: costPerHour.cost_per_hour,
        borderColor: seriesColors[0],
        backgroundColor: seriesColors[0],
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHitRadius: 12,
        tension: 0.15,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y} ${currency}/h` } },
      },
      scales: { y: { beginAtZero: true } },
    },
  });
}

hbarChart('topTitlesChart', topTitles, 'hours');

wireTable('watchTable', 'watchSearch', 'watchCount');
