(() => {
  const formulaPrefix = /^[\s\u0000-\u001f]*[=+\-@]/;

  function escapeCell(value) {
    const text = String(value ?? '');
    const safeText = typeof value === 'number' || !formulaPrefix.test(text)
      ? text
      : `'${text}`;
    return `"${safeText.replaceAll('"', '""')}"`;
  }

  globalThis.SalesMISCsv = Object.freeze({
    serialize(rows) {
      return rows.map(row => row.map(escapeCell).join(',')).join('\r\n');
    },
  });
})();
