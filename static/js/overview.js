const data = JSON.parse(document.getElementById('page-data').textContent);
const { hoursPerMonth, topTitles } = data;

lineChart('hoursChart', hoursPerMonth.months, hoursPerMonth.series, 'hours');
hbarChart('topTitlesChart', topTitles, 'hours');

wireTable('watchTable', 'watchSearch', 'watchCount');
