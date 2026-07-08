(() => {
  const enhanceFigureControls = () => {
    const figure = document.querySelector(".interactive-figure");
    const note = figure?.querySelector(".figure-note");
    const title = note?.querySelector("strong");
    const body = note?.querySelector("p");
    const controls = Array.from(figure?.querySelectorAll(".figure-control") || []);
    if (!figure || !title || !body || controls.length === 0) return;

    const activate = (control) => {
      controls.forEach((item) => item.classList.toggle("is-active", item === control));
      title.textContent = control.dataset.title || "";
      body.textContent = control.dataset.body || "";
    };

    controls.forEach((control) => {
      control.addEventListener("mouseenter", () => activate(control));
      control.addEventListener("focus", () => activate(control));
      control.addEventListener("click", (event) => {
        event.preventDefault();
        activate(control);
      });
    });
  };

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

  enhanceFigureControls();
  enhanceBenchmarkTable();
})();
