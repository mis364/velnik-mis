(() => {
  function dateAt(key) {
    return new Date(`${key}T00:00:00Z`);
  }

  function dateKey(date) {
    return date.toISOString().slice(0, 10);
  }

  function plusDay(key, amount) {
    const value = dateAt(key);
    value.setUTCDate(value.getUTCDate() + amount);
    return dateKey(value);
  }

  function total(items, key) {
    return items.reduce((sum, row) => sum + (Number(row[key]) || 0), 0);
  }

  function aggregate(items, start, end) {
    const map = new Map();
    for (const row of items) {
      if (row.date < start || row.date > end) continue;
      map.set(row.label, (map.get(row.label) || 0) + (Number(row.value) || 0));
    }
    return [...map.entries()].map(([label, value]) => ({ label, value }));
  }

  function comparisonPeriods(from, to) {
    const dayCount = Math.round((dateAt(to) - dateAt(from)) / 86400000) + 1;
    const previousTo = plusDay(from, -1);
    const previousFrom = plusDay(previousTo, -(dayCount - 1));
    return { from, to, previousFrom, previousTo };
  }

  function periodComparison(history, from, to) {
    const { previousFrom, previousTo } = comparisonPeriods(from, to);
    if (!history || history.start > previousFrom || history.end < previousTo) {
      return { available: false, from, to, previousFrom, previousTo };
    }
    const current = total(history.daily.filter(row => row.date >= from && row.date <= to), 'net');
    const previous = total(history.daily.filter(row => row.date >= previousFrom && row.date <= previousTo), 'net');
    const stateTotals = (start, end) => {
      const totals = new Map();
      for (const row of aggregate(history.stateByDay, start, end)) {
        const key = row.label.trim().toUpperCase();
        const existing = totals.get(key);
        totals.set(key, {
          label: existing?.label || row.label,
          value: (existing?.value || 0) + row.value,
        });
      }
      return totals;
    };
    const currentStates = stateTotals(from, to);
    const previousStates = stateTotals(previousFrom, previousTo);
    const states = [...new Set([...currentStates.keys(), ...previousStates.keys()])]
      .map(key => {
        const currentSales = currentStates.get(key)?.value || 0;
        const previousSales = previousStates.get(key)?.value || 0;
        return {
          state: currentStates.get(key)?.label || previousStates.get(key).label,
          currentSales,
          previousSales,
          change: currentSales - previousSales,
          changePct: previousSales ? (currentSales - previousSales) / Math.abs(previousSales) * 100 : null,
        };
      })
      .sort((a, b) => Math.abs(b.change) - Math.abs(a.change) || a.state.localeCompare(b.state));
    return {
      available: true,
      from,
      to,
      previousFrom,
      previousTo,
      current,
      previous,
      change: current - previous,
      changePct: previous ? (current - previous) / Math.abs(previous) * 100 : null,
      states,
    };
  }

  function matchingDateLastYear(key) {
    const date = dateAt(key);
    const year = date.getUTCFullYear() - 1;
    const month = date.getUTCMonth();
    const day = Math.min(date.getUTCDate(), new Date(Date.UTC(year, month + 1, 0)).getUTCDate());
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  function yearOverYearComparison(currentHistory, lastYearHistory, from, to) {
    const previousFrom = matchingDateLastYear(from);
    const previousTo = matchingDateLastYear(to);
    if (!lastYearHistory || lastYearHistory.start > previousFrom || lastYearHistory.end < previousTo) {
      return { available: false, from, to, previousFrom, previousTo };
    }
    const current = total(currentHistory.daily.filter(row => row.date >= from && row.date <= to), 'net');
    const previous = total(lastYearHistory.daily.filter(row => row.date >= previousFrom && row.date <= previousTo), 'net');
    const stateTotals = (source, start, end) => {
      const totals = new Map();
      for (const row of aggregate(source, start, end)) {
        const key = row.label.trim().toUpperCase();
        const existing = totals.get(key);
        totals.set(key, {
          label: existing?.label || row.label,
          value: (existing?.value || 0) + row.value,
        });
      }
      return totals;
    };
    const currentStates = stateTotals(currentHistory.stateByDay, from, to);
    const previousStates = stateTotals(lastYearHistory.stateByDay, previousFrom, previousTo);
    const states = [...new Set([...currentStates.keys(), ...previousStates.keys()])]
      .map(key => {
        const currentSales = currentStates.get(key)?.value || 0;
        const previousSales = previousStates.get(key)?.value || 0;
        return {
          state: currentStates.get(key)?.label || previousStates.get(key).label,
          currentSales,
          previousSales,
          change: currentSales - previousSales,
          changePct: previousSales ? (currentSales - previousSales) / Math.abs(previousSales) * 100 : null,
        };
      })
      .sort((a, b) => Math.abs(b.change) - Math.abs(a.change) || a.state.localeCompare(b.state));
    return {
      available: true,
      from,
      to,
      previousFrom,
      previousTo,
      current,
      previous,
      change: current - previous,
      changePct: previous ? (current - previous) / Math.abs(previous) * 100 : null,
      states,
    };
  }

  function stockBillingOpportunities(comparison, inventory) {
    if (!comparison?.available || !inventory?.states?.length) return [];
    const stockByName = new Map(inventory.states.map(row => [row.state.trim().toUpperCase(), Number(row.total) || 0]));
    const matched = comparison.states.filter(row => stockByName.has(row.state.trim().toUpperCase()));
    if (matched.length < 2) return [];
    const median = values => {
      const sorted = [...values].sort((a, b) => a - b);
      const middle = Math.floor(sorted.length / 2);
      return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
    };
    const stockMedian = median(matched.map(row => stockByName.get(row.state.trim().toUpperCase())));
    const billingMedian = median(matched.map(row => row.currentSales));
    return matched
      .filter(row =>
        stockByName.get(row.state.trim().toUpperCase()) > stockMedian &&
        row.currentSales < billingMedian
      )
      .map(row => ({ ...row, stock: stockByName.get(row.state.trim().toUpperCase()) }))
      .sort((a, b) => b.stock - a.stock || a.currentSales - b.currentSales);
  }

  globalThis.SalesMISAnalysis = Object.freeze({
    matchingDateLastYear,
    periodComparison,
    stockBillingOpportunities,
    yearOverYearComparison,
  });
})();
