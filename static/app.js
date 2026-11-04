const DATA = JSON.parse(document.getElementById('report-data').textContent);
if (!DATA.available) {
  document.body.classList.add('no-sales-workbook');
  document.querySelectorAll('main.page > section:not(.hero):not(#recurring)').forEach(section => {
    section.style.display = 'none';
  });
  document.querySelectorAll('nav a').forEach(link => {
    if (link.getAttribute('href') !== '#recurring' &&
        !['/backup-download', '/logout'].includes(link.getAttribute('href'))) {
      link.style.display = 'none';
    }
  });
  document.querySelector('.hero-copy').textContent =
    'Upload your sales workbook to start viewing the report.';
  document.getElementById('periodLabel').textContent = 'Awaiting workbook';
  document.getElementById('sourceLoadedAt').textContent = 'No sales workbook uploaded yet';
  document.getElementById('sourceName').textContent = 'No workbook uploaded';
  const recurringHeading = document.querySelector('#recurring h2');
  if (recurringHeading) recurringHeading.textContent = 'Upload your first sales workbook';
  const refreshHeading = document.querySelector('#recurring .refresh-panel h3');
  if (refreshHeading) refreshHeading.textContent = 'Start the sales report';
  const uploadStatus = document.getElementById('uploadStatus');
  if (uploadStatus) {
    uploadStatus.textContent =
      'Choose an .xlsx workbook with the Raw and SS to DB Sale sheets.';
  }
  const refreshNote = document.querySelector('#recurring .refresh-panel .muted.small');
  if (refreshNote) {
    refreshNote.textContent =
      'After upload, the report will load automatically and the workbook will synchronize to private S3 storage.';
  }
  const workbookFile = document.getElementById('workbookFile');
  if (workbookFile) workbookFile.addEventListener('change', async event => {
    const file = event.target.files[0];
    if (!file) return;
    const status = document.getElementById('uploadStatus');
    status.textContent = `Uploading ${file.name}…`;
    status.classList.remove('error');
    const form = new FormData();
    form.append('workbook', file);
    try {
      const response = await fetch('/upload', { method: 'POST', body: form });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'Upload failed.');
      status.textContent = 'Workbook uploaded. Loading the dashboard…';
      location.reload();
    } catch (error) {
      status.textContent = error.message || 'Upload failed.';
      status.classList.add('error');
    } finally {
      event.target.value = '';
    }
  });
} else {
const REPORT_ANALYSIS = globalThis.SalesMISAnalysis;
const PAGE_SIZE = 25;
let pageNumber = 0;
const money = value => new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value) || 0);
const perPerson = value => new Intl.NumberFormat('en-IN', { minimumFractionDigits: 4, maximumFractionDigits: 4 }).format(Number(value) || 0);
const whole = value => new Intl.NumberFormat('en-IN').format(Number(value) || 0);
const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const stateLabel = value => String(value || 'Unclassified').trim();

function fromTo() {
  return { from: document.getElementById('dateFrom').value, to: document.getElementById('dateTo').value };
}
function fullReportSelected() {
  const { from, to } = fromTo();
  return from <= DATA.period.start && to >= DATA.period.end;
}
function includedNepalAmount() {
  return fullReportSelected() && DATA.nepalManual?.includedInPeriod ? Number(DATA.nepalManual.manualValue) || 0 : 0;
}
function selectDaily() {
  const { from, to } = fromTo();
  return DATA.daily.filter(row => row.date >= from && row.date <= to).sort((a, b) => a.date.localeCompare(b.date));
}
function dateAt(key) { return new Date(`${key}T00:00:00Z`); }
function dateKey(date) { return date.toISOString().slice(0, 10); }
function plusDay(key, amount) { const value = dateAt(key); value.setUTCDate(value.getUTCDate() + amount); return dateKey(value); }
function dayText(key, year = false) {
  return dateAt(key).toLocaleDateString('en-GB', year ? { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' } : { day: '2-digit', month: 'short', timeZone: 'UTC' });
}
function total(items, key) { return items.reduce((sum, row) => sum + (Number(row[key]) || 0), 0); }
function aggregate(items, start, end) {
  const map = new Map();
  for (const row of items) {
    if (row.date < start || row.date > end) continue;
    map.set(row.label, (map.get(row.label) || 0) + (Number(row.value) || 0));
  }
  return [...map.entries()].map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
}

function renderPeriodComparison() {
  const { from, to } = fromTo();
  const comparison = REPORT_ANALYSIS.periodComparison(DATA.history, from, to);
  const status = document.getElementById('comparisonStatus');
  const summary = document.getElementById('comparisonSummary');
  const rows = document.getElementById('comparisonRows');
  const stockWarning = DATA.stockStateError
    ? ` Stock/billing review flags are unavailable: ${DATA.stockStateError}`
    : '';
  if (!comparison.available) {
    status.textContent = `Cannot compare ${dayText(comparison.from, true)}–${dayText(comparison.to, true)} yet: the uploaded sales workbook does not cover the full previous period (${dayText(comparison.previousFrom, true)}–${dayText(comparison.previousTo, true)}). Upload a workbook containing those dates.${stockWarning}`;
    summary.innerHTML = '';
    rows.innerHTML = '<tr><td colspan="5" class="empty">Previous-period data is unavailable.</td></tr>';
    return;
  }
  const changeLabel = comparison.changePct === null
    ? 'No percentage baseline (previous sales were zero)'
    : `${comparison.changePct > 0 ? '+' : ''}${comparison.changePct.toFixed(1)}%`;
  status.textContent = `Selected ${dayText(comparison.from, true)}–${dayText(comparison.to, true)} vs preceding equal-length period ${dayText(comparison.previousFrom, true)}–${dayText(comparison.previousTo, true)}.${stockWarning}`;
  summary.innerHTML = [
    ['Previous period sales', `${money(comparison.previous)} lakh`],
    ['Selected period sales', `${money(comparison.current)} lakh`],
    ['Change', `${money(comparison.change)} lakh`],
    ['Change %', changeLabel],
  ].map(([label, value]) => `<article class="stat"><span class="stat-label">${safe(label)}</span><strong class="stat-value">${safe(value)}</strong></article>`).join('');
  rows.innerHTML = comparison.states.length
    ? comparison.states.slice(0, 10).map(row => `<tr><td>${safe(row.state)}</td><td class="num">${money(row.previousSales)}</td><td class="num">${money(row.currentSales)}</td><td class="num ${row.change < 0 ? 'gap' : ''}">${row.change > 0 ? '+' : ''}${money(row.change)}</td><td class="num">${row.changePct === null ? '—' : `${row.changePct > 0 ? '+' : ''}${row.changePct.toFixed(1)}%`}</td></tr>`).join('')
    : '<tr><td colspan="5" class="empty">No state/region billing is available in these periods.</td></tr>';
}

function renderYearOverYearComparison() {
  const { from, to } = fromTo();
  const comparison = REPORT_ANALYSIS.yearOverYearComparison(
    DATA.history,
    DATA.lastYearData?.history,
    from,
    to
  );
  const status = document.getElementById('yearComparisonStatus');
  const summary = document.getElementById('yearComparisonSummary');
  const rows = document.getElementById('yearComparisonRows');
  if (!DATA.lastYearData) {
    status.textContent = DATA.lastYearError
      ? `The last-year workbook could not be read: ${DATA.lastYearError}`
      : 'Upload the separate FY 2025–26 workbook above to enable this comparison.';
    summary.innerHTML = '';
    rows.innerHTML = '<tr><td colspan="5" class="empty">Last-year sales data is not loaded.</td></tr>';
    return;
  }
  if (!comparison.available) {
    status.textContent = `The uploaded workbook (${DATA.lastYearData.source}) does not cover the full matching period ${dayText(comparison.previousFrom, true)}–${dayText(comparison.previousTo, true)}.`;
    summary.innerHTML = '';
    rows.innerHTML = '<tr><td colspan="5" class="empty">Matching prior-year dates are unavailable.</td></tr>';
    return;
  }
  status.textContent = `Selected ${dayText(comparison.from, true)}–${dayText(comparison.to, true)} compared with ${dayText(comparison.previousFrom, true)}–${dayText(comparison.previousTo, true)} from ${DATA.lastYearData.source}.`;
  const changeLabel = comparison.changePct === null
    ? 'No percentage baseline (last-year sales were zero)'
    : `${comparison.changePct > 0 ? '+' : ''}${comparison.changePct.toFixed(1)}%`;
  summary.innerHTML = [
    ['Last-year sales', `${money(comparison.previous)} lakh`],
    ['Current-year sales', `${money(comparison.current)} lakh`],
    ['Change', `${money(comparison.change)} lakh`],
    ['Change %', changeLabel],
  ].map(([label, value]) => `<article class="stat"><span class="stat-label">${safe(label)}</span><strong class="stat-value">${safe(value)}</strong></article>`).join('');
  rows.innerHTML = comparison.states.length
    ? comparison.states.slice(0, 10).map(row => `<tr><td>${safe(row.state)}</td><td class="num">${money(row.previousSales)}</td><td class="num">${money(row.currentSales)}</td><td class="num ${row.change < 0 ? 'gap' : ''}">${row.change > 0 ? '+' : ''}${money(row.change)}</td><td class="num">${row.changePct === null ? '—' : `${row.changePct > 0 ? '+' : ''}${row.changePct.toFixed(1)}%`}</td></tr>`).join('')
    : '<tr><td colspan="5" class="empty">No state/region billing is available in these periods.</td></tr>';
}

function downloadActionReport() {
  const { from, to } = fromTo();
  const comparison = REPORT_ANALYSIS.periodComparison(DATA.history, from, to);
  const rows = [['Section', 'State / region', 'Current period', 'Previous period', 'Change', 'Change %', 'Stock (workbook units)', 'Suggested follow-up']];
  if (comparison.available) {
    rows.push([
      'Period comparison',
      'All states / regions',
      `${comparison.from} to ${comparison.to} · ${money(comparison.current)} lakh`,
      `${comparison.previousFrom} to ${comparison.previousTo} · ${money(comparison.previous)} lakh`,
      `${money(comparison.change)} lakh`,
      comparison.changePct === null ? 'N/A (previous sales were zero)' : `${comparison.changePct.toFixed(1)}%`,
      '',
      'Review major changes against coverage, order timing, and source data.',
    ]);
    for (const state of comparison.states) {
      rows.push([
        'State billing change',
        state.state,
        `${money(state.currentSales)} lakh`,
        `${money(state.previousSales)} lakh`,
        `${money(state.change)} lakh`,
        state.changePct === null ? 'N/A (previous sales were zero)' : `${state.changePct.toFixed(1)}%`,
        '',
        state.change < 0 ? 'Review billing decline, coverage, and open orders.' : 'Review drivers of growth and repeat successful actions.',
      ]);
    }
    for (const row of REPORT_ANALYSIS.stockBillingOpportunities(comparison, DATA.stockStateData)) {
      rows.push([
        'High stock / low billing review',
        row.state,
        `${money(row.currentSales)} lakh`,
        `${money(row.previousSales)} lakh`,
        `${money(row.change)} lakh`,
        row.changePct === null ? 'N/A (previous sales were zero)' : `${row.changePct.toFixed(1)}%`,
        money(row.stock),
        'Check stock availability, order conversion, recent demand, and dispatch constraints before action.',
      ]);
    }
  } else {
    rows.push([
      'Period comparison unavailable',
      '',
      `${comparison.from} to ${comparison.to}`,
      `${comparison.previousFrom} to ${comparison.previousTo}`,
      '',
      '',
      '',
      'Upload a sales workbook containing the full previous equal-length period.',
    ]);
  }
  const yearComparison = REPORT_ANALYSIS.yearOverYearComparison(
    DATA.history,
    DATA.lastYearData?.history,
    from,
    to
  );
  if (yearComparison.available) {
    rows.push([
      'Year-over-year comparison',
      'All states / regions',
      `${yearComparison.from} to ${yearComparison.to} · ${money(yearComparison.current)} lakh`,
      `${yearComparison.previousFrom} to ${yearComparison.previousTo} · ${money(yearComparison.previous)} lakh`,
      `${money(yearComparison.change)} lakh`,
      yearComparison.changePct === null ? 'N/A (last-year sales were zero)' : `${yearComparison.changePct.toFixed(1)}%`,
      '',
      'Review major changes against market coverage, order timing, and source data.',
    ]);
    for (const state of yearComparison.states) {
      rows.push([
        'Year-over-year state billing',
        state.state,
        `${money(state.currentSales)} lakh`,
        `${money(state.previousSales)} lakh`,
        `${money(state.change)} lakh`,
        state.changePct === null ? 'N/A (last-year sales were zero)' : `${state.changePct.toFixed(1)}%`,
        '',
        state.change < 0 ? 'Review billing decline, coverage, and open orders.' : 'Review drivers of growth and repeat successful actions.',
      ]);
    }
  } else {
    rows.push([
      'Year-over-year comparison unavailable',
      '',
      yearComparison.from,
      yearComparison.to,
      '',
      '',
      '',
      DATA.lastYearData
        ? `Uploaded last-year workbook does not cover ${yearComparison.previousFrom} to ${yearComparison.previousTo}.`
        : 'Upload a separate last-year sales workbook to enable this comparison.',
    ]);
  }
  for (const plan of DATA.statePlan || []) {
    if (plan.gap > 0) {
      rows.push([
        'Plan gap',
        plan.state,
        `${money(plan.achievement)} lakh achievement`,
        `${money(plan.plan)} lakh plan`,
        `${money(plan.gap)} lakh gap`,
        `${(plan.pct * 100).toFixed(1)}% achieved`,
        '',
        'Review coverage and open orders; confirm against the source workbook.',
      ]);
    }
    if (DATA.stockStateError) {
      rows.push([
        'Stock data unavailable',
        '',
        '',
        '',
        '',
        '',
        '',
        `Could not build the stock summary: ${DATA.stockStateError}`,
      ]);
    }
  }
  const csv = SalesMISCsv.serialize(rows);
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }));
  link.download = `sales-action-report-${fromTo().from}-to-${fromTo().to}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

function renderStats(days) {
  const { from, to } = fromTo();
  const currentDay = days.find(row => row.date === to);
  const rawSales = total(days, 'net');
  const sales = rawSales + includedNepalAmount();
  const gross = total(days, 'gross');
  const lines = total(days, 'lines');
  const missing = total(days, 'missingNet');
  const kpis = DATA.executiveKpis || {};
  const plan = Number(kpis.planTotal) || 0;
  const achievement = fullReportSelected() ? (Number(kpis.netTotal) || sales) : sales;
  const achievementPct = plan ? achievement / plan : null;
  const projection = Number(kpis.projectedMonthEnd) || 0;
  const forecastVariance = Number(kpis.forecastVariance) || 0;
  const growth = REPORT_ANALYSIS.periodComparison(DATA.history, from, to);
  const growthText = growth.available && growth.changePct !== null
    ? `${growth.changePct >= 0 ? '+' : ''}${growth.changePct.toFixed(1)}% vs previous period`
    : 'Previous-period baseline unavailable';
  const cards = [
    { label: 'MTD sales', value: money(achievement) + ' lakh', note: growthText, tone: growth.available && growth.changePct < 0 ? 'negative' : 'positive' },
    { label: 'Monthly plan', value: money(plan) + ' lakh', note: `${kpis.elapsedDays || 0} of ${kpis.daysInMonth || 0} days elapsed`, tone: 'neutral' },
    { label: 'Plan achievement', value: achievementPct === null ? '—' : achievementPct.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%', note: `${money(achievement)} lakh achieved`, tone: achievementPct >= 1 ? 'positive' : achievementPct >= 0.8 ? 'warning' : 'negative' },
    { label: 'Projected month end', value: money(projection) + ' lakh', note: `${forecastVariance >= 0 ? '+' : ''}${money(forecastVariance)} lakh vs plan`, tone: forecastVariance >= 0 ? 'positive' : 'negative' },
    { label: 'Remaining plan gap', value: money(Number(kpis.remainingGap) || Math.max(0, plan - achievement)) + ' lakh', note: `${kpis.daysRemaining || 0} days remaining`, tone: (Number(kpis.remainingGap) || Math.max(0, plan - achievement)) <= 0 ? 'positive' : 'warning' },
    { label: 'Sales on ' + dayText(to), value: money(currentDay?.net) + ' lakh', note: 'Without GST · gross ' + money(currentDay?.gross) + ' lakh', tone: 'neutral' },
    { label: 'Active zero-billing distributors', value: whole(DATA.quality.activeZeroBilling), note: 'Follow-up action list available', tone: DATA.quality.activeZeroBilling > 0 ? 'warning' : 'positive' },
    { label: 'Missing net values', value: whole(missing), note: 'Of ' + whole(lines) + ' sales lines', tone: missing > 0 ? 'negative' : 'positive' },
  ];
  document.getElementById('stats').innerHTML = cards.map(card => `
    <article class="stat kpi-${safe(card.tone)}"><span class="stat-label">${safe(card.label)}</span><strong class="stat-value">${safe(card.value)}</strong><span class="stat-note">${safe(card.note)}</span></article>`).join('');
  document.getElementById('periodLabel').textContent = `${dayText(from, true)} – ${dayText(to, true)}`;
  document.getElementById('dailyCaption').textContent = `${dayText(from)}–${dayText(to)} · ${money(rawSales)} lakh from dated Raw transactions`;
}

function renderWeeklyPerformance() {
  const weekly = DATA.weeklyPerformance || { available: false };
  const content = document.getElementById('weeklyContent');
  const empty = document.getElementById('weeklyEmpty');
  content.hidden = !weekly.available;
  empty.hidden = Boolean(weekly.available);
  if (!weekly.available) return;

  document.getElementById('weeklyPeriod').textContent = weekly.weekLabel || 'WEEK';
  document.getElementById('weeklyCaption').textContent = `Weekly plan and achievement from ${weekly.source}.`;
  const weeklyUploadStatus = document.getElementById('weeklyUploadStatus');
  if (weeklyUploadStatus) weeklyUploadStatus.textContent = `Current source: ${weekly.source} · loaded ${weekly.loadedAt}`;
  const weeklyWarnings = document.getElementById('weeklyWarnings');
  weeklyWarnings.innerHTML = (weekly.warnings || []).length
    ? `<h3>Weekly data checks</h3><ul>${weekly.warnings.map(warning => `<li>${safe(warning)}</li>`).join('')}</ul>`
    : '';
  const summary = weekly.summary;
  document.getElementById('weeklyStats').innerHTML = [
    ['Week plan', `${money(summary.plan)} lakh`],
    ['Week achievement', `${money(summary.achievement)} lakh`],
    ['Balance', `${money(summary.balance)} lakh`],
    ['Overall achievement', `${summary.plan ? (summary.achievement / summary.plan * 100).toFixed(1) : '0.0'}%`],
  ].map(([label, value]) => `<article class="stat"><span class="stat-label">${safe(label)}</span><strong class="stat-value">${safe(value)}</strong></article>`).join('');

  const insights = weekly.growthInsights || {};
  const insightCards = [];
  if (insights.bestAttainment) {
    const row = insights.bestAttainment;
    insightCards.push({
      label: 'Strongest plan attainment',
      title: row.state,
      value: `${(row.pct * 100).toFixed(1)}% of plan`,
      body: 'Review what is working in this region and consider whether the approach can be repeated elsewhere.',
    });
  }
  if (insights.largestBalance) {
    const row = insights.largestBalance;
    insightCards.push({
      label: 'Largest remaining plan balance',
      title: row.state,
      value: `${money(row.balance)} lakh`,
      body: `${row.pct === null ? 'No plan attainment percentage is available.' : `${(row.pct * 100).toFixed(1)}% of its week plan achieved.`} Review distributor coverage and follow-up capacity here.`,
    });
  }
  document.getElementById('weeklyInsights').innerHTML = insightCards.map((card, index) => `
    <article class="insight"><span class="insight-index">${String(index + 1).padStart(2, '0')}</span><span class="insight-label">${safe(card.label)}</span><h3>${safe(card.title)}</h3><strong>${safe(card.value)}</strong><p>${safe(card.body)}</p></article>
  `).join('');
  document.getElementById('weeklyRows').innerHTML = weekly.states.map(row => `
    <tr><td>${safe(row.state)}</td><td class="num">${row.plan === null ? '—' : money(row.plan)}</td><td class="num">${row.achievement === null ? '—' : money(row.achievement)}</td><td class="num"><span class="achievement">${row.pct === null ? '—' : `${(row.pct * 100).toFixed(1)}%`}</span></td><td class="num ${row.balance > 0 ? 'gap' : ''}">${row.balance === null ? '—' : money(row.balance)}</td></tr>
  `).join('');
}

function renderDaily(days) {
  const { from, to } = fromTo();
  const dayRows = [];
  for (let key = from; key <= to; key = plusDay(key, 1)) {
    dayRows.push(days.find(row => row.date === key) || { date: key, net: 0, lines: 0 });
  }
  if (!dayRows.length) { document.getElementById('dailyChart').innerHTML = '<p class="empty">No sales in the selected dates.</p>'; return; }
  const width = 780, height = 250, left = 46, right = 16, top = 24, bottom = 42;
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const maximum = Math.max(...dayRows.map(row => Number(row.net) || 0), 1);
  const step = plotWidth / dayRows.length, barWidth = Math.max(3, Math.min(26, step * .58));
  let grid = '';
  for (let i = 0; i <= 4; i++) {
    const y = top + plotHeight * i / 4, label = maximum * (1 - i / 4);
    grid += `<line class="chart-grid" x1="${left}" x2="${width-right}" y1="${y}" y2="${y}"/><text class="axis-label" x="${left-7}" y="${y+4}" text-anchor="end">${money(label)}</text>`;
  }
  let bars = '';
  dayRows.forEach((row, index) => {
    const value = Number(row.net) || 0, x = left + index * step + (step - barWidth) / 2;
    const barHeight = Math.max(value ? 2 : 0, value / maximum * plotHeight), y = top + plotHeight - barHeight;
    const labelTick = dayRows.length <= 12 || index === 0 || index === dayRows.length - 1 || (index + 1) % 5 === 0;
    const valueText = dayRows.length <= 10 || index === dayRows.length - 1 ? `<text class="bar-value" x="${x+barWidth/2}" y="${Math.max(13,y-6)}" text-anchor="middle">${money(value)}</text>` : '';
    bars += `<rect class="sales-bar ${row.date === to ? 'latest' : ''}" x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="3"><title>${safe(dayText(row.date))}: ${money(value)} lakh</title></rect>${valueText}${labelTick ? `<text class="axis-label" x="${x+barWidth/2}" y="${height-16}" text-anchor="middle">${safe(dayText(row.date))}</text>` : ''}`;
  });
  document.getElementById('dailyChart').innerHTML = `<svg class="daily-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Daily sales without GST in lakh">${grid}${bars}</svg>`;
}

function renderBarList(elementId, rows, limit = Infinity, unit = 'lakh') {
  const target = document.getElementById(elementId);
  const visible = rows.slice(0, limit);
  if (!visible.length) { target.innerHTML = '<p class="empty">No figures are available for this selection.</p>'; return; }
  const max = Math.max(...visible.map(row => Number(row.value) || 0), 1);
  target.innerHTML = visible.map(row => `<div class="mix-row">
    <span class="mix-name" title="${safe(row.label)}">${safe(row.label)}</span>
    <div class="mix-track" aria-hidden="true"><span style="width:${Math.max(1, (Number(row.value)||0) / max * 100)}%"></span></div>
    <strong class="mix-value">${money(row.value)} <small>${safe(unit)}</small></strong>
  </div>`).join('');
}

function renderMix(days) {
  const { from, to } = fromTo();
  const includeNepal = includedNepalAmount() > 0;
  const products = aggregate(DATA.productByDay, from, to);
  if (includeNepal && DATA.nepalManual) {
    for (const item of DATA.nepalManual.productSales || []) {
      const existing = products.find(row => row.label === item.product);
      if (existing) existing.value += Number(item.value) || 0;
      else products.push({ label: item.product, value: Number(item.value) || 0 });
    }
    products.sort((a,b)=>b.value-a.value);
  }
  renderBarList('productBars', products);
  const allSales = total(days, 'net') + includedNepalAmount();
  const topFiveShare = allSales ? products.slice(0, 5).reduce((sum, row) => sum + row.value, 0) / allSales : 0;
  document.getElementById('productCaption').textContent = `${products.length} product groups · top five account for ${Math.round(topFiveShare * 100)}% of sales in this period.${includeNepal ? ' Includes Nepal summary product values.' : ''}`;
}

function renderStateBilling() {
  const { from, to } = fromTo();
  const billingByKey = new Map(aggregate(DATA.stateByDay, from, to)
    .map(row => [row.label.trim().toUpperCase(), row.value]));
  const consumedKeys = new Set();
  const rows = [];
  for (const region of DATA.populationRegions || []) {
    const memberKeys = region.members.map(member => member.trim().toUpperCase());
    const fallbackKeys = region.fallbackMembers.map(member => member.trim().toUpperCase());
    const presentMembers = memberKeys.filter(key => billingByKey.has(key));
    const keys = presentMembers.length
      ? presentMembers
      : fallbackKeys.filter(key => billingByKey.has(key));
    if (!keys.length) continue;
    for (const key of [...memberKeys, ...fallbackKeys]) consumedKeys.add(key);
    rows.push({
      label: region.state === 'NESSA' ? 'Nessa' : region.state,
      value: keys.reduce((sum, key) => sum + billingByKey.get(key), 0),
      population: region.population,
    });
  }
  for (const [key, value] of billingByKey) {
    if (!consumedKeys.has(key)) rows.push({ label: key, value, population: null });
  }
  if (includedNepalAmount() > 0 && DATA.nepalManual) {
    rows.push({ label: 'NP (Nepal · manual summary)', value: DATA.nepalManual.manualValue, population: null });
  }
  rows.sort((a, b) => b.value - a.value || a.label.localeCompare(b.label));
  const billingTotal = rows.reduce((sum, row) => sum + row.value, 0);
  const caption = `${dayText(from)}–${dayText(to)} · ${money(billingTotal)} lakh total billing · ${rows.length} states / regions`;
  document.getElementById('stateBillingCaption').textContent = caption;
  renderBarList('stateBillingChart', rows, rows.length);
  const perCapitaRanks = new Map();
  const rankedPerCapita = rows
    .filter(row => row.population && row.value >= 0)
    .map(row => ({ ...row, perCapita: row.value * 100000 / row.population }))
    .sort((a, b) => b.perCapita - a.perCapita || a.label.localeCompare(b.label));
  let priorPerCapita;
  let rank = 0;
  rankedPerCapita.forEach((row, index) => {
    if (index === 0 || row.perCapita !== priorPerCapita) rank = index + 1;
    perCapitaRanks.set(row.label, rank);
    priorPerCapita = row.perCapita;
  });
  document.getElementById('stateBillingRows').innerHTML = rows.length
    ? rows.map((row, index) => {
      const perCapita = row.population ? row.value * 100000 / row.population : null;
      return `<tr><td>${index + 1}</td><td>${safe(row.label)}</td><td class="num">${money(row.value)}</td><td class="num">${perCapitaRanks.get(row.label) ?? '—'}</td><td class="num">${row.population ? whole(row.population) : '—'}</td><td class="num">${perCapita === null ? '—' : `₹${perPerson(perCapita)}`}</td><td class="num">${billingTotal ? (row.value / billingTotal * 100).toFixed(1) : '0.0'}%</td></tr>`;
    }).join('')
    : '<tr><td colspan="7" class="empty">No state billing is available for the selected period.</td></tr>';
  document.getElementById('populationSourceLabel').textContent = DATA.populationSource;
  document.getElementById('populationSourceLink').href = DATA.populationSourceUrl;
}

function activeZeroByState() {
  return Object.entries(DATA.zeroByState || {}).sort((a, b) => b[1] - a[1]);
}
function renderInsights() {
  const plan = DATA.statePlan || [];
  const largestGap = [...plan].sort((a, b) => b.gap - a.gap)[0];
  const lowestPct = [...plan].filter(row => row.plan > 0).sort((a, b) => a.pct - b.pct)[0];
  const zeroStates = activeZeroByState();
  const topZero = zeroStates[0];
  const topProduct = DATA.productMix?.[0];
  const cards = [];
  if (largestGap) {
    const zeroCount = DATA.zeroByState?.[largestGap.state] || 0;
    cards.push({ label: 'Largest plan gap', title: largestGap.state, value: `${money(largestGap.gap)} lakh below plan`, body: `${(largestGap.pct*100).toFixed(1)}% achieved. ${whole(zeroCount)} active zero-billing distributors are listed in this state / region.`, action: 'Review this state’s zero-billing list and confirm the target is current.' });
  }
  if (lowestPct && lowestPct.state !== largestGap?.state) {
    cards.push({ label: 'Lowest plan achievement', title: lowestPct.state, value: `${(lowestPct.pct*100).toFixed(1)}% of plan`, body: `${money(lowestPct.achievement)} lakh achieved against ${money(lowestPct.plan)} lakh planned.`, action: 'Check coverage, order frequency, and whether the plan is still appropriate.' });
  }
  if (topZero) {
    cards.push({ label: 'Most zero-billing distributors', title: topZero[0], value: `${whole(topZero[1])} active distributors`, body: 'Highest count by state / region in the source follow-up list.', action: 'Review the account list with the responsible sales representative.' });
  }
  if (topProduct) {
    cards.push({ label: 'Product concentration', title: topProduct.product, value: `${(topProduct.share*100).toFixed(1)}% of sales`, body: `${money(topProduct.value)} lakh in the reporting month.`, action: 'Check availability and sales coverage for other product groups.' });
  }
  document.getElementById('insights').innerHTML = cards.map((card, index) => `<article class="insight"><span class="insight-index">0${index+1}</span><span class="insight-label">${safe(card.label)}</span><h3>${safe(card.title)}</h3><strong>${safe(card.value)}</strong><p>${safe(card.body)}</p><div class="next-step"><b>Suggested check</b><span>${safe(card.action)}</span></div></article>`).join('');

  const rows = [...plan].sort((a,b)=>b.gap-a.gap);
  document.getElementById('planRows').innerHTML = rows.length ? rows.map(row => `<tr><td>${safe(row.state)}${row.manual ? ' <span class="manual-tag">manual</span>' : ''}</td><td class="num">${money(row.plan)}</td><td class="num">${money(row.achievement)}</td><td class="num"><span class="achievement">${(row.pct*100).toFixed(1)}%</span></td><td class="num gap">${money(row.gap)}</td></tr>`).join('') : '<tr><td colspan="5" class="empty">No state plan data found in the Without GST sheet.</td></tr>';
  document.getElementById('planCaption').textContent = plan.length ? `Using “${DATA.planColumns.plan}” and “${DATA.planColumns.achievement}” from Without GST. Sorted by largest remaining gap.` : 'Upload a workbook with plan and achievement columns to show state gaps.';

  const issues = [];
  if (DATA.quality.missingNet) issues.push(`${whole(DATA.quality.missingNet)} sales lines are missing a Without GST value.`);
  if (DATA.quality.missingTariff) issues.push(`${whole(DATA.quality.missingTariff)} lines have a missing or nonnumeric tariff.`);
  if (DATA.quality.duplicateRows) issues.push(`${whole(DATA.quality.duplicateRows)} lines share the same voucher, distributor, and item key; review before treating them as duplicates.`);
  const last = dateAt(DATA.period.end);
  const header = String(DATA.summaryDateHeader || '');
  if (header && !header.toLowerCase().includes(last.toLocaleDateString('en-GB',{month:'short',timeZone:'UTC'}).toLowerCase())) {
    issues.push(`The Without GST sheet shows “${header}” as its date heading, while Raw transactions end ${dayText(DATA.period.end,true)}. The page uses Raw dates for the report period.`);
  }
  const badRecs = (DATA.reconciliation || []).filter(row => !row.manual && !row.matches);
  if (badRecs.length) issues.push(`${badRecs.length} state / region achievement totals do not match Raw within 0.02 lakh. Check the source formulas or exclusions.`);
  else if (DATA.reconciliation?.length) issues.push('State / region achievements reconcile with Raw within 0.02 lakh.');
  if (DATA.nepalManual?.includedInPeriod) issues.push(`Nepal summary achievement of ${money(DATA.nepalManual.manualValue)} lakh is included in the period total, state chart, and product mix. Raw has no Nepal transaction dates, so it is not spread across the daily chart.`);
  document.getElementById('qualityNotes').innerHTML = issues.length ? `<h3>Data checks</h3><ul>${issues.map(issue=>`<li>${safe(issue)}</li>`).join('')}</ul>` : '';
  const dateWarning = document.getElementById('dateWarning');
  if (dateWarning) dateWarning.textContent = DATA.loadedAt ? `Last loaded: ${DATA.loadedAt}` : '';
}

function renderNepalPanel() {
  const nepal = DATA.nepalManual;
  const target = document.getElementById('nepalPanel');
  if (!nepal) { target.innerHTML = '<article class="panel">No NP summary row was found in the Without GST sheet.</article>'; return; }
  const pct = Number(nepal.achievementPct) || (nepal.plan ? nepal.achievement / nepal.plan : 0);
  const productRows = (nepal.productSales || []).map((item,index) => `<label>${safe(item.product)}<input type="number" step="0.01" min="0" data-nepal-product="${index}" value="${Number(item.value||0).toFixed(2)}"></label>`).join('');
  const ownerControls = document.body.dataset.owner === 'true';
  const editForm = ownerControls ? `<form id="nepalManualForm" class="panel nepal-form"><h3>Update Nepal figures</h3><p class="muted small">Enter amounts in lakh. Saving updates the report for this reporting month.</p><div class="nepal-input-grid"><label>Monthly plan<input name="plan" type="number" step="0.01" value="${Number(nepal.plan||0).toFixed(2)}" required></label><label>Monthly billing achievement<input name="achievement" id="nepalAchievement" type="number" step="0.01" value="${Number(nepal.achievement||0).toFixed(2)}" required></label><label>Billing on ${safe(nepal.dailyHeader || 'summary date')}<input name="dailyBilling" type="number" step="0.01" value="${Number(nepal.dailyBilling||0).toFixed(2)}" required></label><label>Today's average plan<input name="todayPlan" type="number" step="0.01" value="${Number(nepal.todayPlan||0).toFixed(2)}" required></label><label>Today's achievement<input name="todayAchievement" type="number" step="0.01" value="${Number(nepal.todayAchievement||0).toFixed(2)}" required></label></div><h4>Nepal product sales (lakh)</h4><div class="nepal-input-grid">${productRows}</div><p class="muted small">If you change only the monthly achievement, Other / Range Value adjusts to balance the Nepal product mix. You can also edit the product amounts.</p><div class="nepal-form-footer"><button class="button primary" type="submit">Save Nepal figures</button><span id="nepalSaveStatus" role="status"></span></div></form>` : '';
  target.innerHTML = `<article class="panel nepal-main"><div class="nepal-metrics"><div class="nepal-metric"><span>Monthly billing achievement</span><strong>${money(nepal.achievement)} lakh</strong><small>Plan ${money(nepal.plan)} lakh · ${(pct*100).toFixed(1)}%</small></div><div class="nepal-metric"><span>Billing on ${safe(nepal.dailyHeader || 'summary date')}</span><strong>${money(nepal.dailyBilling)} lakh</strong><small>Dated summary value</small></div><div class="nepal-metric"><span>Today's average plan</span><strong>${money(nepal.todayPlan)} lakh</strong><small>Today's achievement ${money(nepal.todayAchievement)} lakh</small></div></div><p class="nepal-note">${nepal.includedInPeriod ? `${money(nepal.achievement)} lakh is included in the period total, Nepal state chart, and product mix.` : 'Nepal transactions already appear in Raw, so the monthly amount is not added twice.'} The daily chart uses dated Raw transactions; the summary does not provide daily Nepal transaction detail.</p></article>${editForm}`;
  if (!ownerControls) return;
  const form = document.getElementById('nepalManualForm');
  const achievementInput = document.getElementById('nepalAchievement');
  const rangeIndex = (nepal.productSales || []).findIndex(item => item.product === 'Other / Range Value');
  function balanceRange() {
    if (rangeIndex < 0) return;
    const rangeInput = form.querySelector(`[data-nepal-product="${rangeIndex}"]`);
    const otherTotal = [...form.querySelectorAll('[data-nepal-product]')].filter(input => Number(input.dataset.nepalProduct) !== rangeIndex).reduce((sum,input)=>sum+(Number(input.value)||0),0);
    rangeInput.value = Math.max(0,(Number(achievementInput.value)||0)-otherTotal).toFixed(2);
  }
  achievementInput.addEventListener('input', balanceRange);
  form.querySelectorAll('[data-nepal-product]').forEach(input => {
    if (Number(input.dataset.nepalProduct) !== rangeIndex) input.addEventListener('input', balanceRange);
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const status = document.getElementById('nepalSaveStatus');
    status.textContent = 'Saving Nepal figures…';
    const payload = Object.fromEntries(new FormData(form).entries());
    for (const key of ['plan','achievement','dailyBilling','todayPlan','todayAchievement']) payload[key] = Number(payload[key]);
    payload.productSales = (nepal.productSales || []).map((item,index) => ({ product:item.product, value:Number(form.querySelector(`[data-nepal-product="${index}"]`).value) }));
    try {
      const response = await fetch('/nepal-manual', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'Could not save Nepal figures.');
      location.reload();
    } catch (error) { status.textContent = error.message || 'Could not save Nepal figures.'; }
  });
}

function filteredDistributors() {
  const search = document.getElementById('followSearch').value.trim().toLowerCase();
  const state = document.getElementById('stateFilter').value;
  const rep = document.getElementById('repFilter').value;
  return DATA.followups.filter(row => (!state || row.state === state) && (!rep || row.salesRep === rep) &&
    (!search || [row.name,row.code,row.state,row.salesRep,row.asm,row.superStockist].some(value => String(value).toLowerCase().includes(search))));
}
function renderDistributors() {
  const rows = filteredDistributors(), pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  pageNumber = Math.min(pageNumber, pageCount - 1);
  const begin = pageNumber * PAGE_SIZE, visible = rows.slice(begin, begin + PAGE_SIZE);
  document.getElementById('followCount').textContent = `${whole(DATA.followups.length)} flagged for follow-up`;
  document.getElementById('pageSummary').textContent = rows.length ? `Showing ${whole(begin+1)}–${whole(Math.min(begin+PAGE_SIZE, rows.length))} of ${whole(rows.length)}` : 'No distributors match the filters.';
  document.getElementById('followRows').innerHTML = visible.length ? visible.map(row => `<tr><td class="strong">${safe(row.name)}</td><td class="code">${safe(row.code)}</td><td>${safe(row.state)}</td><td>${safe(row.salesRep || '—')}</td><td>${safe(row.asm || '—')}</td><td>${safe(row.superStockist || '—')}</td></tr>`).join('') : '<tr><td class="empty" colspan="6">No distributors match the filters.</td></tr>';
  document.getElementById('prevPage').disabled = pageNumber === 0;
  document.getElementById('nextPage').disabled = pageNumber >= pageCount - 1;
}
function fillOptions(id, items, key, firstLabel) {
  const select = document.getElementById(id), previous = select.value;
  const values = [...new Set(items.map(row => row[key]).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
  select.innerHTML = `<option value="">${safe(firstLabel)}</option>` + values.map(value => `<option value="${safe(value)}">${safe(value)}</option>`).join('');
  if (values.includes(previous)) select.value = previous;
}
function render() {
  const days = selectDaily();
  renderStats(days); renderPeriodComparison(); renderYearOverYearComparison(); renderDaily(days); renderMix(days); renderStateBilling(); renderInsights(); renderDistributors();
}

const fromInput = document.getElementById('dateFrom'), toInput = document.getElementById('dateTo');
fromInput.value = DATA.period.start; toInput.value = DATA.period.end;
for (const input of [fromInput, toInput]) { input.min = DATA.period.start; input.max = DATA.period.end; }
document.getElementById('sourceName').textContent = DATA.source;
document.getElementById('sourceLoadedAt').textContent = `Latest workbook loaded: ${DATA.loadedAt}`;
const uploadStatus = document.getElementById('uploadStatus');
if (uploadStatus) uploadStatus.textContent = `Latest workbook: ${DATA.source} · uploaded ${DATA.loadedAt}`;
const weeklyStatus = document.getElementById('weeklyUploadStatus');
if (weeklyStatus) weeklyStatus.textContent = DATA.weeklyPerformance?.available
  ? `Current source: ${DATA.weeklyPerformance.source} · loaded ${DATA.weeklyPerformance.loadedAt}`
  : 'No weekly plan workbook is loaded.';
const lastYearStatus = document.getElementById('lastYearUploadStatus');
if (lastYearStatus) lastYearStatus.textContent = DATA.lastYearData
  ? `Current source: ${DATA.lastYearData.source} · loaded ${DATA.lastYearData.loadedAt}`
  : DATA.lastYearError
    ? `Workbook unavailable: ${DATA.lastYearError}`
    : 'No last-year workbook uploaded.';
document.getElementById('applyDates').addEventListener('click', () => {
  if (fromInput.value > toInput.value) [fromInput.value, toInput.value] = [toInput.value, fromInput.value];
  render();
});
document.getElementById('downloadActionReport').addEventListener('click', downloadActionReport);
fillOptions('stateFilter', DATA.followups, 'state', 'All states / regions');
fillOptions('repFilter', DATA.followups, 'salesRep', 'All representatives');
for (const id of ['followSearch','stateFilter','repFilter']) document.getElementById(id).addEventListener(id === 'followSearch' ? 'input' : 'change', () => { pageNumber = 0; renderDistributors(); });
document.getElementById('prevPage').addEventListener('click', () => { pageNumber = Math.max(0,pageNumber-1); renderDistributors(); });
document.getElementById('nextPage').addEventListener('click', () => { pageNumber++; renderDistributors(); });
document.getElementById('downloadCsv').addEventListener('click', () => {
  const rows = filteredDistributors(), header = ['Distributor','DB code','State / region','Sales representative','Area manager','Super stockist'];
  const fields = ['name','code','state','salesRep','asm','superStockist'];
  const csv = SalesMISCsv.serialize([header, ...rows.map(row => fields.map(key => row[key] || ''))]);
  const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));link.download='active-zero-billing-follow-up.csv';link.click();URL.revokeObjectURL(link.href);
});
const workbookFile = document.getElementById('workbookFile');
if (workbookFile) workbookFile.addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  const status = document.getElementById('uploadStatus'); status.textContent = `Uploading ${file.name}…`;
  const form = new FormData(); form.append('workbook', file);
  try {
    const response = await fetch('/upload', { method: 'POST', body: form });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'Upload failed.');
    location.reload();
  } catch (error) {
    status.textContent = error.message || 'Upload failed.'; status.classList.add('error');
  } finally { event.target.value = ''; }
});
const lastYearWorkbookFile = document.getElementById('lastYearWorkbookFile');
if (lastYearWorkbookFile) lastYearWorkbookFile.addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  const status = document.getElementById('lastYearUploadStatus');
  status.textContent = `Uploading ${file.name}…`;
  status.classList.remove('error');
  const form = new FormData(); form.append('workbook', file);
  try {
    const response = await fetch('/last-year-upload', { method: 'POST', body: form });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'Last-year workbook upload failed.');
    location.reload();
  } catch (error) {
    status.textContent = error.message || 'Last-year workbook upload failed.';
    status.classList.add('error');
  } finally { event.target.value = ''; }
});
const weeklyWorkbookFile = document.getElementById('weeklyWorkbookFile');
if (weeklyWorkbookFile) weeklyWorkbookFile.addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  const status = document.getElementById('weeklyUploadStatus'); status.textContent = `Uploading ${file.name}…`;
  status.classList.remove('error');
  const form = new FormData(); form.append('workbook', file);
  try {
    const response = await fetch('/weekly-upload', { method: 'POST', body: form });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'Weekly plan upload failed.');
    location.reload();
  } catch (error) {
    status.textContent = error.message || 'Weekly plan upload failed.';
    status.classList.add('error');
  } finally { event.target.value = ''; }
});
renderWeeklyPerformance();
renderNepalPanel();
render();
}
