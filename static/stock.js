const DATA = JSON.parse(document.getElementById('stock-data').textContent);
const PAGE_SIZE = 25;
let pageNumber = 0;
let detailPageNumber = 0;
const DETAIL_PAGE_SIZE = 25;
const numberFormat = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const amount = value => numberFormat.format(Number(value) || 0);
const whole = value => new Intl.NumberFormat('en-IN').format(Number(value) || 0);
const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

function renderBars(elementId, rows, labelKey, valueKey, limit = Infinity) {
  const target = document.getElementById(elementId);
  const visible = rows.slice(0, limit);
  if (!visible.length) {
    target.innerHTML = '<p class="empty">No figures are available.</p>';
    return;
  }
  const maximum = Math.max(...visible.map(row => Number(row[valueKey]) || 0), 1);
  target.innerHTML = visible.map(row => `<div class="mix-row">
    <span class="mix-name" title="${safe(row[labelKey])}">${safe(row[labelKey])}</span>
    <div class="mix-track" aria-hidden="true"><span style="width:${Math.max(1, (Number(row[valueKey]) || 0) / maximum * 100)}%"></span></div>
    <strong class="mix-value">${amount(row[valueKey])}</strong>
  </div>`).join('');
}

function filteredDistributors() {
  const search = document.getElementById('stockSearch').value.trim().toLowerCase();
  const state = document.getElementById('stockStateFilter').value;
  return (DATA.distributors || []).filter(row =>
    (!state || row.state === state) &&
    (!search || `${row.name} ${row.state} ${row.type}`.toLowerCase().includes(search))
  );
}

function renderDistributors() {
  const rows = filteredDistributors();
  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  pageNumber = Math.min(pageNumber, pageCount - 1);
  const begin = pageNumber * PAGE_SIZE;
  const visible = rows.slice(begin, begin + PAGE_SIZE);
  document.getElementById('stockDistributorCount').textContent = `${whole(DATA.summary.distributorCount)} stock points`;
  document.getElementById('stockPageSummary').textContent = rows.length
    ? `Showing ${whole(begin + 1)}–${whole(Math.min(begin + PAGE_SIZE, rows.length))} of ${whole(rows.length)}`
    : 'No stock points match the filters.';
  document.getElementById('stockDistributorRows').innerHTML = visible.length
    ? visible.map(row => `<tr><td>${safe(row.type || '—')}</td><td>${safe(row.state)}</td><td>${safe(row.name)}</td><td class="num">${amount(row.total)}</td><td class="num ${row.negativeItems ? 'negative-stock' : ''}">${whole(row.negativeItems)}</td></tr>`).join('')
    : '<tr><td class="empty" colspan="5">No stock points match the filters.</td></tr>';
  document.getElementById('stockPrevPage').disabled = pageNumber === 0;
  document.getElementById('stockNextPage').disabled = pageNumber >= pageCount - 1;
}

function filteredStockDetails() {
  const search = document.getElementById('stockDetailSearch')?.value.trim().toLowerCase() || '';
  const state = document.getElementById('stockDetailStateFilter')?.value || '';
  const product = document.getElementById('stockDetailProductFilter')?.value || '';
  return (DATA.stateProductDetails || []).filter(row =>
    (!state || row.state === state) &&
    (!product || row.product === product) &&
    (!search || `${row.state} ${row.product} ${row.sku} ${row.particulars} ${row.attribute}`.toLowerCase().includes(search))
  );
}

function renderStockDetails() {
  const rows = filteredStockDetails();
  const pageCount = Math.max(1, Math.ceil(rows.length / DETAIL_PAGE_SIZE));
  detailPageNumber = Math.min(detailPageNumber, pageCount - 1);
  const begin = detailPageNumber * DETAIL_PAGE_SIZE;
  const visible = rows.slice(begin, begin + DETAIL_PAGE_SIZE);
  document.getElementById('stockDetailCount').textContent = `${whole(rows.length)} detailed rows`;
  const summaryRows = DATA.stateProductSummary || [];
  document.getElementById('stockDetailSummaryRows').innerHTML = summaryRows.length
    ? summaryRows.map(row => `<tr><td>${safe(row.state)}</td><td>${safe(row.product)}</td><td>${safe(row.type)}</td><td class="num ${row.quantity < 0 ? 'negative-stock' : ''}">${amount(row.quantity)}</td><td class="num ${row.value < 0 ? 'negative-stock' : ''}">${amount(row.value)}</td></tr>`).join('')
    : '<tr><td class="empty" colspan="5">No state and product summary is available.</td></tr>';
  document.getElementById('stockDetailPageSummary').textContent = rows.length
    ? `Showing ${whole(begin + 1)}–${whole(Math.min(begin + DETAIL_PAGE_SIZE, rows.length))} of ${whole(rows.length)}`
    : 'No detailed stock rows match the filters.';
  document.getElementById('stockDetailRows').innerHTML = visible.length
    ? visible.map(row => `<tr><td>${safe(row.state || '—')}</td><td>${safe(row.product || '—')}</td><td><strong>${safe(row.sku || '—')}</strong><br><span class="muted small">${safe(row.particulars || '—')}</span></td><td>${safe(row.attribute || '—')}</td><td>${safe(row.type || '—')}</td><td class="num ${row.quantity < 0 ? 'negative-stock' : ''}">${amount(row.quantity)}</td><td class="num ${row.value < 0 ? 'negative-stock' : ''}">${amount(row.value)}</td></tr>`).join('')
    : '<tr><td class="empty" colspan="7">No detailed stock rows match the filters.</td></tr>';
  document.getElementById('stockDetailPrevPage').disabled = detailPageNumber === 0;
  document.getElementById('stockDetailNextPage').disabled = detailPageNumber >= pageCount - 1;
}

function populateReport() {
  document.getElementById('stockContent').hidden = false;
  document.getElementById('stockEmpty').hidden = true;
  document.getElementById('stockSource').textContent = DATA.source;
  document.getElementById('stockDate').textContent = DATA.reportDate || '—';
  const uploadStatus = document.getElementById('stockUploadStatus');
  if (uploadStatus) uploadStatus.textContent = `Current source: ${DATA.source} · loaded ${DATA.loadedAt}`;
  const stats = [
    ['Total stock', amount(DATA.summary.totalStock), 'From Item Stock CS & SS Stock'],
    ['CS stock', amount(DATA.summary.csStock), 'Stock-point balance'],
    ['SS stock', amount(DATA.summary.ssStock), 'Stock-point balance'],
    ['Negative stock', amount(DATA.summary.negativeStock), `${whole(DATA.summary.negativeProductCount)} products with negative balances`],
    ['NPD stock', amount(DATA.summary.npdStock), 'Reported separately'],
    ['Stock points', whole(DATA.summary.distributorCount), 'Listed in the Stock sheet'],
  ];
  document.getElementById('stock-summary').innerHTML = stats.map(row => `<article class="stat"><span class="stat-label">${safe(row[0])}</span><strong class="stat-value ${row[0] === 'Negative stock' ? 'negative-stock' : ''}">${safe(row[1])}</strong><span class="stat-note">${safe(row[2])}</span></article>`).join('');
  renderBars('stockProductBars', DATA.products || [], 'item', 'total', 10);
  renderBars('stockStateBars', DATA.states || [], 'state', 'total', 12);
  document.getElementById('stockProductRows').innerHTML = (DATA.products || []).map(row =>
    `<tr><td>${safe(row.item)}</td><td class="num">${amount(row.cs)}</td><td class="num">${amount(row.ss)}</td><td class="num">${amount(row.total)}</td><td class="num ${row.negative < 0 ? 'negative-stock' : ''}">${amount(row.negative)}</td></tr>`
  ).join('') || '<tr><td class="empty" colspan="5">No product stock was found.</td></tr>';

  const stateFilter = document.getElementById('stockStateFilter');
  const states = DATA.stateColumns || [];
  stateFilter.innerHTML = '<option value="">All states / regions</option>' + states.map(state => `<option value="${safe(state)}">${safe(state)}</option>`).join('');
  const detailRows = DATA.stateProductDetails || [];
  const detailStates = [...new Set(detailRows.map(row => row.state).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const detailProducts = [...new Set(detailRows.map(row => row.product).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  document.getElementById('stockDetailStateFilter').innerHTML = '<option value="">All states</option>' + detailStates.map(state => `<option value="${safe(state)}">${safe(state)}</option>`).join('');
  document.getElementById('stockDetailProductFilter').innerHTML = '<option value="">All products</option>' + detailProducts.map(product => `<option value="${safe(product)}">${safe(product)}</option>`).join('');
  document.getElementById('stockDetailSearch').addEventListener('input', () => { detailPageNumber = 0; renderStockDetails(); });
  document.getElementById('stockDetailStateFilter').addEventListener('change', () => { detailPageNumber = 0; renderStockDetails(); });
  document.getElementById('stockDetailProductFilter').addEventListener('change', () => { detailPageNumber = 0; renderStockDetails(); });
  document.getElementById('stockDetailPrevPage').addEventListener('click', () => { detailPageNumber = Math.max(0, detailPageNumber - 1); renderStockDetails(); });
  document.getElementById('stockDetailNextPage').addEventListener('click', () => { detailPageNumber++; renderStockDetails(); });
  document.getElementById('downloadStockDetailCsv').addEventListener('click', () => {
    const rows = filteredStockDetails();
    const csv = SalesMISCsv.serialize([
      ['State', 'Product', 'SKU', 'Particulars', 'Distributor / Attribute', 'Type', 'Quantity', 'Value'],
      ...rows.map(row => [row.state, row.product, row.sku, row.particulars, row.attribute, row.type, row.quantity, row.value])
    ]);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }));
    link.download = 'state-wise-product-stock-detail.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  });
  renderStockDetails();

  document.getElementById('stockSearch').addEventListener('input', () => { pageNumber = 0; renderDistributors(); });
  stateFilter.addEventListener('change', () => { pageNumber = 0; renderDistributors(); });
  document.getElementById('stockPrevPage').addEventListener('click', () => { pageNumber = Math.max(0, pageNumber - 1); renderDistributors(); });
  document.getElementById('stockNextPage').addEventListener('click', () => { pageNumber++; renderDistributors(); });
  document.getElementById('downloadStockCsv').addEventListener('click', () => {
    const state = stateFilter.value;
    const stateColumns = DATA.stateColumns || [];
    const columns = state ? [state] : stateColumns;
    const header = ['Product', 'Particulars', ...columns, 'Grand Total'];
    const rows = DATA.stateProductRows || [];
    const csv = SalesMISCsv.serialize([header, ...rows.map(row => [
      row.item,
      row.particulars,
      ...columns.map(column => row.values?.[column] ?? ''),
      row.grandTotal ?? ''
    ])]);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }));
    link.download = state ? `state-wise-stock-${state.replace(/[^a-z0-9_-]/gi, '-')}.csv` : 'state-wise-stock-all-states.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  });
  renderDistributors();
}

const uploadInput = document.getElementById('stockWorkbookFile');
if (uploadInput) uploadInput.addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  const status = document.getElementById('stockUploadStatus');
  status.textContent = `Uploading ${file.name}…`;
  status.classList.remove('error');
  const form = new FormData();
  form.append('workbook', file);
  try {
    const response = await fetch('/stock-upload', { method: 'POST', body: form });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'Stock workbook upload failed.');
    location.reload();
  } catch (error) {
    status.textContent = error.message || 'Stock workbook upload failed.';
    status.classList.add('error');
  } finally {
    event.target.value = '';
  }
});

if (DATA.available === false) {
  document.getElementById('stockEmpty').hidden = false;
} else {
  populateReport();
}
