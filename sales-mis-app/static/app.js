const DATA = JSON.parse(document.getElementById('report-data').textContent);
const PAGE_SIZE = 25;
let pageNumber = 0;
const money = value => new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value) || 0);
const whole = value => new Intl.NumberFormat('en-IN').format(Number(value) || 0);
const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const stateLabel = value => String(value || 'Unclassified').trim();

function fromTo() {
  return { from: document.getElementById('dateFrom').value, to: document.getElementById('dateTo').value };
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

function renderStats(days) {
  const { from, to } = fromTo();
  const currentDay = days.find(row => row.date === to);
  const sales = total(days, 'net');
  const gross = total(days, 'gross');
  const lines = total(days, 'lines');
  const missing = total(days, 'missingNet');
  const cards = [
    ['Sales on ' + dayText(to), money(currentDay?.net) + ' lakh', 'Without GST'],
    ['Selected-period sales', money(sales) + ' lakh', 'With tax: ' + money(gross) + ' lakh'],
    ['Active zero-billing distributors', whole(DATA.quality.activeZeroBilling), 'Flagged in the source workbook'],
    ['Missing net values', whole(missing), 'Of ' + whole(lines) + ' sales lines'],
  ];
  document.getElementById('stats').innerHTML = cards.map(card => `
    <article class="stat"><span class="stat-label">${safe(card[0])}</span><strong class="stat-value">${safe(card[1])}</strong><span class="stat-note">${safe(card[2])}</span></article>`).join('');
  document.getElementById('periodLabel').textContent = `${dayText(from, true)} – ${dayText(to, true)}`;
  document.getElementById('dailyCaption').textContent = `${dayText(from)}–${dayText(to)} · ${money(sales)} lakh without GST`;
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
  renderBarList('stateBars', aggregate(DATA.stateByDay, from, to), 8);
  const products = aggregate(DATA.productByDay, from, to);
  renderBarList('productBars', products);
  const allSales = total(days, 'net');
  const topFiveShare = allSales ? products.slice(0, 5).reduce((sum, row) => sum + row.value, 0) / allSales : 0;
  document.getElementById('productCaption').textContent = `${products.length} product groups · top five account for ${Math.round(topFiveShare * 100)}% of sales in this period.`;
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
  document.getElementById('planRows').innerHTML = rows.length ? rows.map(row => `<tr><td>${safe(row.state)}</td><td class="num">${money(row.plan)}</td><td class="num">${money(row.achievement)}</td><td class="num"><span class="achievement">${(row.pct*100).toFixed(1)}%</span></td><td class="num gap">${money(row.gap)}</td></tr>`).join('') : '<tr><td colspan="5" class="empty">No state plan data found in the Without GST sheet.</td></tr>';
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
  const badRecs = (DATA.reconciliation || []).filter(row => !row.matches);
  if (badRecs.length) issues.push(`${badRecs.length} state / region achievement totals do not match Raw within 0.02 lakh. Check the source formulas or exclusions.`);
  else if (DATA.reconciliation?.length) issues.push('State / region achievements reconcile with Raw within 0.02 lakh.');
  document.getElementById('qualityNotes').innerHTML = issues.length ? `<h3>Data checks</h3><ul>${issues.map(issue=>`<li>${safe(issue)}</li>`).join('')}</ul>` : '';
  document.getElementById('dateWarning').textContent = DATA.loadedAt ? `Last loaded: ${DATA.loadedAt}` : '';
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
  renderStats(days); renderDaily(days); renderMix(days); renderInsights(); renderDistributors();
}

const fromInput = document.getElementById('dateFrom'), toInput = document.getElementById('dateTo');
fromInput.value = DATA.period.start; toInput.value = DATA.period.end;
for (const input of [fromInput, toInput]) { input.min = DATA.period.start; input.max = DATA.period.end; }
document.getElementById('sourceName').textContent = DATA.source;
document.getElementById('uploadStatus').textContent = `Current source: ${DATA.source} · loaded ${DATA.loadedAt}`;
document.getElementById('applyDates').addEventListener('click', () => {
  if (fromInput.value > toInput.value) [fromInput.value, toInput.value] = [toInput.value, fromInput.value];
  render();
});
fillOptions('stateFilter', DATA.followups, 'state', 'All states / regions');
fillOptions('repFilter', DATA.followups, 'salesRep', 'All representatives');
for (const id of ['followSearch','stateFilter','repFilter']) document.getElementById(id).addEventListener(id === 'followSearch' ? 'input' : 'change', () => { pageNumber = 0; renderDistributors(); });
document.getElementById('prevPage').addEventListener('click', () => { pageNumber = Math.max(0,pageNumber-1); renderDistributors(); });
document.getElementById('nextPage').addEventListener('click', () => { pageNumber++; renderDistributors(); });
document.getElementById('downloadCsv').addEventListener('click', () => {
  const rows = filteredDistributors(), header = ['Distributor','DB code','State / region','Sales representative','Area manager','Super stockist'];
  const fields = ['name','code','state','salesRep','asm','superStockist'];
  const csv = [header,...rows.map(row=>fields.map(key=>row[key]||''))].map(line=>line.map(value=>'"'+String(value).replaceAll('"','""')+'"').join(',')).join('\r\n');
  const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));link.download='active-zero-billing-follow-up.csv';link.click();URL.revokeObjectURL(link.href);
});
document.getElementById('workbookFile').addEventListener('change', async event => {
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
render();
