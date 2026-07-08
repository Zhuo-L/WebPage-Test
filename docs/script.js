(() => {
  const enhanceBenchmarkTable = () => {
    const table = document.querySelector(".results-table");
    const body = table?.tBodies?.[0];
    if (!table || !body) return;

    const rows = Array.from(body.rows);
    if (!rows.length) return;
    const columnCount = rows[0].cells.length;
    const parseValue = (cell) => {
      const value = Number(cell.textContent.replace(/[^\d.-]/g, ""));
      return Number.isFinite(value) ? value : null;
    };

    for (let column = 1; column < columnCount; column += 1) {
      const values = rows
        .map((row) => ({ cell: row.cells[column], value: parseValue(row.cells[column]) }))
        .filter((item) => item.value !== null);
      if (!values.length) continue;
      const max = Math.max(...values.map((item) => item.value));
      values
        .filter((item) => item.value === max)
        .forEach((item) => item.cell.classList.add("best-in-column"));
    }
  };

  enhanceBenchmarkTable();
})();
