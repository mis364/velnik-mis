const DATA = JSON.parse(document.getElementById('billing-data').textContent);
const PAGE_SIZE = 25;
let pageNumber = 0;
const numberFormat = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const wholeFormat = new Intl.NumberFormat('en-IN');
const amount = value => numberFormat.format(Number(value) || 0);
const whole = value => wholeFormat.format(Number(value) || 0);
const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const bySales = (left, right) => right.salesLakh - left.salesLakh || left.label.localeCompare(right.label);

function selectedMonth() {
  return document.getElementById('billingMonthFilter').value;
}

function currentRows(rows) {
  return rows.filter(row => row.month === selectedMonth());
}

function renderBreakdown(elementId, rows, labelKey, showZero) {
  const target = document.getElementById(elementId);
  const values = currentRows(rows).map(row => ({ ...row, label: row[labelKey] })).sort(bySales);
  target.innerHTML = values.length
    ? values.map(row => `<tr><td>${safe(row.label)}</td><td class="num">${amount(row.salesLakh)}</td><td class="num">${whole(row.activeDbCount)}</td><td class="num">${whole(row.billedActiveDbCount)}</td>${showZero ? `<td class="num">${whole(row.zeroBillingActiveDbCount)}</td>` : ''}<td class="num">${amount(row.efficiencyPct)}%</td></tr>`).join('')
    : `<tr><td class="empty" colspan="${showZero ? 6 : 5}">No figures are available.</td></tr>`;
}

function renderZeroBilling() {
  const month = selectedMonth();
  const state = document.getElementById('zeroBillingStateFilter').value;
  const search = document.getElementById('zeroBillingSearch').value.trim().toLowerCase();
  const rows = DATA.zeroBilling.filter(row =>
    row.month === month &&
    (!state || row.state === state) &&
    (!search || `${row.dbCode} ${row.dbName} ${row.state} ${row.zone} ${row.ssName} ${row.representative}`.toLowerCase().includes(search))
  );
  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  pageNumber = Math.min(pageNumber, pageCount - 1);
  const begin = pageNumber * PAGE_SIZE;
  const visible = rows.slice(begin, begin + PAGE_SIZE);
  document.getElementById('zeroBillingCount').textContent = `${whole(rows.length)} distributors`;
  document.getElementById('zeroBillingPageSummary').textContent = rows.length
    ? `Showing ${whole(begin + 1)}–${whole(Math.min(begin + PAGE_SIZE, rows.length))} of ${whole(rows.length)}`
    : 'No distributors match the selected filters.';
  document.getElementById('zeroBillingRows').innerHTML = visible.length
    ? visible.map(row => `<tr><td>${safe(row.dbCode)}</td><td>${safe(row.dbName)}</td><td>${safe(row.state)}</td><td>${safe(row.zone)}</td><td>${safe(row.ssName)}</td><td>${safe(row.representative)}</td></tr>`).join('')
    : '<tr><td class="empty" colspan="6">No distributors match the selected filters.</td></tr>';
  document.getElementById('zeroBillingPrev').disabled = pageNumber === 0;
  document.getElementById('zeroBillingNext').disabled = pageNumber >= pageCount - 1;
}

function renderSelectedMonth() {
  const month = selectedMonth();
  const summary = DATA.monthly.find(row => row.month === month);
  const stats = [
    ['Billing sales', `${amount(summary.salesLakh)} lakh`, 'Value In Lacs from the workbook'],
    ['Active distributors', whole(summary.activeDbCount), 'Unique distributor codes'],
    ['Billed active distributors', whole(summary.billedActiveDbCount), 'Positive Value In Lacs'],
    ['Billing efficiency', `${amount(summary.efficiencyPct)}%`, 'Billed active DBs ÷ active DBs'],
    ['Active zero billing', whole(summary.zeroBillingActiveDbCount), 'No positive net billing'],
  ];
  document.getElementById('billingStats').innerHTML = stats.map(row => `<article class="stat"><span class="stat-label">${safe(row[0])}</span><strong class="stat-value">${safe(row[1])}</strong><span class="stat-note">${safe(row[2])}</span></article>`).join('');
  document.getElementById('billingTerritoryCaption').textContent = `Selected month: ${month}.`;
  renderBreakdown('billingStateRows', DATA.states, 'state', false);
  renderBreakdown('billingZoneRows', DATA.zones, 'zone', false);
  renderBreakdown('billingRepRows', DATA.representatives, 'representative', true);

  const products = currentRows(DATA.products).sort((left, right) =>
    right.billedDistributors - left.billedDistributors || left.product.localeCompare(right.product)
  );
  document.getElementById('billingProductRows').innerHTML = products.length
    ? products.map(row => `<tr><td>${safe(row.product)}</td><td class="num">${whole(row.billedDistributors)}</td><td class="num">${amount(row.activeCoveragePct)}%</td></tr>`).join('')
    : '<tr><td class="empty" colspan="3">No product columns are available.</td></tr>';

  pageNumber = 0;
  renderZeroBilling();
}

function renderMonthComparison() {
  const monthA = document.getElementById('billingCompareMonthA').value;
  const monthB = document.getElementById('billingCompareMonthB').value;
  const first = DATA.monthly.find(row => row.month === monthA);
  const second = DATA.monthly.find(row => row.month === monthB);
  const summaryTarget = document.getElementById('billingComparisonSummary');
  const rowsTarget = document.getElementById('billingComparisonRows');
  const caption = document.getElementById('billingCompareCaption');
  document.getElementById('billingCompareHeadA').textContent = `${monthA} sales (lakh)`;
  document.getElementById('billingCompareHeadB').textContent = `${monthB} sales (lakh)`;
  caption.textContent = 'Change is second month minus first month. The table shows the 10 largest state / region changes by absolute value. Percentage change is not shown when first-month sales are zero.';
  if (!first || !second) {
    summaryTarget.innerHTML = '';
    rowsTarget.innerHTML = '<tr><td class="empty" colspan="5">Choose two months with data to compare.</td></tr>';
    return;
  }

  const signedAmount = value => `${value > 0 ? '+' : ''}${amount(value)}`;
  const signedWhole = value => `${value > 0 ? '+' : ''}${whole(value)}`;
  const signedPercent = value => `${value > 0 ? '+' : ''}${amount(value)} pp`;
  const metrics = [
    ['Billing sales', `${amount(first.salesLakh)} lakh`, `${amount(second.salesLakh)} lakh`, `${signedAmount(second.salesLakh - first.salesLakh)} lakh`],
    ['Billed active DBs', whole(first.billedActiveDbCount), whole(second.billedActiveDbCount), signedWhole(second.billedActiveDbCount - first.billedActiveDbCount)],
    ['Billing efficiency', `${amount(first.efficiencyPct)}%`, `${amount(second.efficiencyPct)}%`, signedPercent(second.efficiencyPct - first.efficiencyPct)],
    ['Active zero billing', whole(first.zeroBillingActiveDbCount), whole(second.zeroBillingActiveDbCount), signedWhole(second.zeroBillingActiveDbCount - first.zeroBillingActiveDbCount)],
  ];
  summaryTarget.innerHTML = metrics.map(([label, valueA, valueB, change]) =>
    `<article class="stat"><span class="stat-label">${safe(label)} · ${safe(monthA)} → ${safe(monthB)}</span><strong class="stat-value">${safe(valueA)} → ${safe(valueB)}</strong><span class="stat-note">Change: ${safe(change)}</span></article>`
  ).join('');

  const byState = new Map();
  for (const row of DATA.states) {
    if (row.month !== monthA && row.month !== monthB) continue;
    const state = row.state || 'Unclassified';
    const current = byState.get(state) || { state, salesA: 0, salesB: 0 };
    if (row.month === monthA) current.salesA = Number(row.salesLakh) || 0;
    if (row.month === monthB) current.salesB = Number(row.salesLakh) || 0;
    byState.set(state, current);
  }
  const states = [...byState.values()].map(row => ({ ...row, change: row.salesB - row.salesA }))
    .sort((left, right) => Math.abs(right.change) - Math.abs(left.change) || left.state.localeCompare(right.state))
    .slice(0, 10);
  rowsTarget.innerHTML = states.length
    ? states.map(row => `<tr><td>${safe(row.state)}</td><td class="num">${amount(row.salesA)}</td><td class="num">${amount(row.salesB)}</td><td class="num ${row.change < 0 ? 'gap' : ''}">${signedAmount(row.change)}</td><td class="num">${row.salesA ? `${row.change > 0 ? '+' : ''}${amount(row.change / row.salesA * 100)}%` : '—'}</td></tr>`).join('')
    : '<tr><td class="empty" colspan="5">No state / region sales are available for these months.</td></tr>';
}

function populateReport() {
  document.getElementById('billingContent').hidden = false;
  document.getElementById('billingEmpty').hidden = true;
  document.getElementById('billingSource').textContent = DATA.source;
  document.getElementById('billingLoadedAt').textContent = `Latest workbook loaded: ${DATA.loadedAt}`;
  const uploadStatus = document.getElementById('billingUploadStatus');
  if (uploadStatus) uploadStatus.textContent = `Current source: ${DATA.source} · loaded ${DATA.loadedAt}`;

  const monthFilter = document.getElementById('billingMonthFilter');
  monthFilter.innerHTML = DATA.months.map(month => `<option value="${safe(month)}">${safe(month)}</option>`).join('');
  monthFilter.value = DATA.months[DATA.months.length - 1];
  const compareOptions = DATA.months.map(month => `<option value="${safe(month)}">${safe(month)}</option>`).join('');
  const compareMonthA = document.getElementById('billingCompareMonthA');
  const compareMonthB = document.getElementById('billingCompareMonthB');
  compareMonthA.innerHTML = compareOptions;
  compareMonthB.innerHTML = compareOptions;
  compareMonthA.value = DATA.months[Math.max(0, DATA.months.length - 2)];
  compareMonthB.value = DATA.months[DATA.months.length - 1];
  document.getElementById('billingMonthlyRows').innerHTML = DATA.monthly.map(row =>
    `<tr><td>${safe(row.month)}</td><td class="num">${amount(row.salesLakh)}</td><td class="num">${whole(row.activeDbCount)}</td><td class="num">${whole(row.billedActiveDbCount)}</td><td class="num">${whole(row.zeroBillingActiveDbCount)}</td><td class="num">${amount(row.efficiencyPct)}%</td></tr>`
  ).join('');
  const states = [...new Set(DATA.zeroBilling.map(row => row.state))].sort((left, right) => left.localeCompare(right));
  document.getElementById('zeroBillingStateFilter').innerHTML =
    '<option value="">All states / regions</option>' + states.map(state => `<option value="${safe(state)}">${safe(state)}</option>`).join('');
  document.getElementById('billingQuality').textContent =
    `Data checks: ${whole(DATA.quality.sourceRows)} source rows · ${whole(DATA.quality.duplicateDistributorMonthRows)} duplicate distributor-month rows · ${whole(DATA.quality.missingSalesValues)} missing sales values · ${whole(DATA.quality.productCount)} product columns.`;

  monthFilter.addEventListener('change', renderSelectedMonth);
  compareMonthA.addEventListener('change', renderMonthComparison);
  compareMonthB.addEventListener('change', renderMonthComparison);
  document.getElementById('zeroBillingStateFilter').addEventListener('change', () => { pageNumber = 0; renderZeroBilling(); });
  document.getElementById('zeroBillingSearch').addEventListener('input', () => { pageNumber = 0; renderZeroBilling(); });
  document.getElementById('zeroBillingPrev').addEventListener('click', () => { pageNumber = Math.max(0, pageNumber - 1); renderZeroBilling(); });
  document.getElementById('zeroBillingNext').addEventListener('click', () => { pageNumber++; renderZeroBilling(); });
  document.getElementById('downloadZeroBilling').addEventListener('click', () => {
    const month = selectedMonth();
    const state = document.getElementById('zeroBillingStateFilter').value;
    const search = document.getElementById('zeroBillingSearch').value.trim().toLowerCase();
    const rows = DATA.zeroBilling.filter(row =>
      row.month === month &&
      (!state || row.state === state) &&
      (!search || `${row.dbCode} ${row.dbName} ${row.state} ${row.zone} ${row.ssName} ${row.representative}`.toLowerCase().includes(search))
    );
    const csv = SalesMISCsv.serialize([
      ['Month', 'DB code', 'Distributor', 'State / region', 'Zone', 'Super stockist', 'Representative'],
      ...rows.map(row => [row.month, row.dbCode, row.dbName, row.state, row.zone, row.ssName, row.representative]),
    ]);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }));
    link.download = `zero-billing-${month.toLowerCase()}${state ? `-${state.replace(/[^a-z0-9_-]/gi, '-')}` : ''}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  });
  renderSelectedMonth();
  renderMonthComparison();
}

const uploadInput = document.getElementById('billingWorkbookFile');
if (uploadInput) uploadInput.addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  const status = document.getElementById('billingUploadStatus');
  status.textContent = `Uploading ${file.name}…`;
  status.classList.remove('error');
  const form = new FormData();
  form.append('workbook', file);
  try {
    const response = await fetch('/billing-efficiency-upload', { method: 'POST', body: form });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'Billing workbook upload failed.');
    location.reload();
  } catch (error) {
    status.textContent = error.message || 'Billing workbook upload failed.';
    status.classList.add('error');
  } finally {
    event.target.value = '';
  }
});

if (DATA.available === false) {
  document.getElementById('billingEmpty').hidden = false;
} else {
  populateReport();
}
