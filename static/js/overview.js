const data = JSON.parse(document.getElementById('page-data').textContent);
const { hoursPerMonth, titlesByMonth, spendPerMonth, currency, topTitles } = data;

const monthSpend = Object.fromEntries(spendPerMonth.months.map((m, i) => [m, spendPerMonth.amounts[i]]));
lineChart('hoursChart', hoursPerMonth.months, hoursPerMonth.series, 'hours', titlesByMonth, monthSpend, currency);
hbarChart('topTitlesChart', topTitles, 'hours');

wireTable('watchTable', 'watchSearch', 'watchCount');
