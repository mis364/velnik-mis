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
  document.getElementById('billingMonthlyRows').innerHTML = DATA.monthly.map(row =>
    `<tr><td>${safe(row.month)}</td><td class="num">${amount(row.salesLakh)}</td><td class="num">${whole(row.activeDbCount)}</td><td class="num">${whole(row.billedActiveDbCount)}</td><td class="num">${whole(row.zeroBillingActiveDbCount)}</td><td class="num">${amount(row.efficiencyPct)}%</td></tr>`
  ).join('');
  const states = [...new Set(DATA.zeroBilling.map(row => row.state))].sort((left, right) => left.localeCompare(right));
  document.getElementById('zeroBillingStateFilter').innerHTML =
    '<option value="">All states / regions</option>' + states.map(state => `<option value="${safe(state)}">${safe(state)}</option>`).join('');
  document.getElementById('billingQuality').textContent =
    `Data checks: ${whole(DATA.quality.sourceRows)} source rows · ${whole(DATA.quality.duplicateDistributorMonthRows)} duplicate distributor-month rows · ${whole(DATA.quality.missingSalesValues)} missing sales values · ${whole(DATA.quality.productCount)} product columns.`;

  monthFilter.addEventListener('change', renderSelectedMonth);
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
