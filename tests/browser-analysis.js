const analysis = globalThis.SalesMISAnalysis;
const results = document.getElementById('test-results');
const failures = [];

function assertEqual(actual, expected, message) {
  if (actual !== expected) throw new Error(`${message}: expected ${expected}, got ${actual}`);
}

function test(name, run) {
  const item = document.createElement('li');
  try {
    run();
    item.textContent = `PASS ${name}`;
  } catch (error) {
    item.textContent = `FAIL ${name}: ${error.message}`;
    failures.push(name);
  }
  results.append(item);
}

test('equal-length comparison totals and groups normalized state names', () => {
  const history = {
    start: '2026-09-01',
    end: '2026-10-10',
    daily: [
      { date: '2026-10-06', net: 5 },
      { date: '2026-10-07', net: 15 },
      { date: '2026-10-08', net: 10 },
      { date: '2026-10-09', net: 30 },
    ],
    stateByDay: [
      { date: '2026-10-06', label: 'UP', value: 5 },
      { date: '2026-10-07', label: 'UP', value: 15 },
      { date: '2026-10-08', label: 'UP', value: 10 },
      { date: '2026-10-09', label: 'up', value: 30 },
    ],
  };
  const comparison = analysis.periodComparison(history, '2026-10-08', '2026-10-09');
  assertEqual(comparison.previousFrom, '2026-10-06', 'previous start');
  assertEqual(comparison.previousTo, '2026-10-07', 'previous end');
  assertEqual(comparison.current, 40, 'selected total');
  assertEqual(comparison.previous, 20, 'previous total');
  assertEqual(comparison.states.length, 1, 'normalized state count');
  assertEqual(comparison.states[0].change, 20, 'state change');
});

test('comparison is unavailable when history misses any prior-period date', () => {
  const comparison = analysis.periodComparison({
    start: '2026-10-07',
    end: '2026-10-09',
    daily: [],
    stateByDay: [],
  }, '2026-10-08', '2026-10-09');
  assertEqual(comparison.available, false, 'availability');
});

test('year-over-year date matching handles leap day', () => {
  const comparison = analysis.yearOverYearComparison({
    daily: [{ date: '2024-02-29', net: 8 }],
    stateByDay: [],
  }, {
    start: '2023-02-28',
    end: '2023-02-28',
    daily: [{ date: '2023-02-28', net: 5 }],
    stateByDay: [],
  }, '2024-02-29', '2024-02-29');
  assertEqual(comparison.available, true, 'availability');
  assertEqual(comparison.previousFrom, '2023-02-28', 'matching prior-year date');
  assertEqual(comparison.current, 8, 'current total');
  assertEqual(comparison.previous, 5, 'prior-year total');
});

test('stock opportunity ranking uses matched-state medians', () => {
  const comparison = {
    available: true,
    states: [
      { state: 'Alpha', currentSales: 5, previousSales: 4, change: 1 },
      { state: 'Beta', currentSales: 10, previousSales: 8, change: 2 },
      { state: 'Gamma', currentSales: 50, previousSales: 40, change: 10 },
      { state: 'Delta', currentSales: 60, previousSales: 55, change: 5 },
    ],
  };
  const inventory = { states: [
    { state: 'ALPHA', total: 100 },
    { state: 'Beta', total: 80 },
    { state: 'Gamma', total: 20 },
    { state: 'Delta', total: 10 },
  ] };
  const opportunities = analysis.stockBillingOpportunities(comparison, inventory);
  assertEqual(opportunities.length, 2, 'opportunity count');
  assertEqual(opportunities[0].state, 'Alpha', 'highest-stock opportunity');
  assertEqual(opportunities[1].state, 'Beta', 'next opportunity');
});

test('CSV exports neutralize formula-like text and preserve numeric values', () => {
  const csv = globalThis.SalesMISCsv.serialize([
    ['=1+1', ' +SUM(A1:A2)', '\t@SUM(A1:A2)', '-4+5', 42, -12],
  ]);
  assertEqual(
    csv,
    '"\'=1+1","\' +SUM(A1:A2)","\'\t@SUM(A1:A2)","\'-4+5","42","-12"',
    'safe CSV serialization'
  );
});

const status = document.getElementById('test-status');
status.textContent = failures.length
  ? `${failures.length} test(s) failed.`
  : 'All 5 browser tests passed.';
document.body.dataset.testStatus = failures.length ? 'failed' : 'passed';
