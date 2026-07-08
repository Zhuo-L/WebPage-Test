(() => {
  const svgNS = "http://www.w3.org/2000/svg";
  const imageSpace = {
    width: 3988,
    height: 1858,
    plot: {
      left: 218,
      right: 3112,
      top: 162,
      bottom: 1420,
    },
  };

  const makeSvg = (name, attrs = {}) => {
    const element = document.createElementNS(svgNS, name);
    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
    return element;
  };

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const setText = (note, title, body) => {
    const noteTitle = note?.querySelector("strong");
    const noteBody = note?.querySelector("p");
    if (noteTitle) noteTitle.textContent = title;
    if (noteBody) noteBody.textContent = body;
  };

  const normalizeLabel = (label) => String(label || "").replace(/\s+/g, " ").trim();

  const markerRadius = (point) => {
    if (point.marker === "star") return 70;
    return Math.max(44, Math.min(146, Math.sqrt(Number(point.size || 400)) * 2.35));
  };

  const renderPerformanceOverlay = () => {
    const data = window.EXOMIND_PERFORMANCE_DATA;
    const container = document.getElementById("performance-chart");
    const panel = data?.panels?.[0];
    const image = container?.querySelector(".chart-fallback");
    if (!container || !panel || !image) return;

    const note = container.closest(".interactive-figure")?.querySelector(".figure-note");
    const controls = Array.from(container.closest(".interactive-figure")?.querySelectorAll(".figure-control") || []);
    const pointMap = new Map(panel.points.map((point) => [point.key, point]));
    const xSpan = panel.xlim[1] - panel.xlim[0];
    const ySpan = panel.ylim[1] - panel.ylim[0];
    const plotWidth = imageSpace.plot.right - imageSpace.plot.left;
    const plotHeight = imageSpace.plot.bottom - imageSpace.plot.top;
    const sx = (x) => imageSpace.plot.left + ((x - panel.xlim[0]) / xSpan) * plotWidth;
    const sy = (y) => imageSpace.plot.bottom - ((y - panel.ylim[0]) / ySpan) * plotHeight;

    const overlay = makeSvg("svg", {
      class: "chart-overlay",
      viewBox: `0 0 ${imageSpace.width} ${imageSpace.height}`,
      role: "group",
      "aria-label": "Interactive areas for the benchmark figure",
      focusable: "false",
    });
    const loupe = document.createElement("div");
    loupe.className = "chart-loupe";
    loupe.setAttribute("aria-hidden", "true");
    let activeTarget = null;

    const addTitle = (element, text) => {
      const title = makeSvg("title");
      title.textContent = text;
      element.appendChild(title);
    };

    const setActiveControl = (key) => {
      controls.forEach((control) => control.classList.toggle("is-active", control.dataset.key === key));
    };

    const showLoupe = (target) => {
      if (!image.clientWidth || !image.clientHeight) return;
      activeTarget = target;
      const zoom = Number(target.zoom || 1.78);
      const displayX = (target.x / imageSpace.width) * image.clientWidth;
      const displayY = (target.y / imageSpace.height) * image.clientHeight;
      const loupeWidth = loupe.offsetWidth || 240;
      const loupeHeight = loupe.offsetHeight || 152;
      const left = clamp(displayX, loupeWidth / 2 + 10, image.clientWidth - loupeWidth / 2 - 10);
      const top = clamp(displayY, loupeHeight / 2 + 10, image.clientHeight - loupeHeight / 2 - 10);
      loupe.style.left = `${left}px`;
      loupe.style.top = `${top}px`;
      loupe.style.backgroundImage = `url("${image.getAttribute("src")}")`;
      loupe.style.backgroundSize = `${image.clientWidth * zoom}px ${image.clientHeight * zoom}px`;
      loupe.style.backgroundPosition = `${-(displayX * zoom - loupeWidth / 2)}px ${-(displayY * zoom - loupeHeight / 2)}px`;
      loupe.classList.add("is-visible");
    };

    const showPoint = (key, controlKey = "") => {
      const point = pointMap.get(key);
      if (!point) return;
      if (controlKey) setActiveControl(controlKey);
      else setActiveControl("");
      showLoupe({
        x: sx(point.x),
        y: sy(point.y),
        zoom: point.key === "Ours" ? 1.62 : 1.78,
      });
      if (point.key === "Ours") {
        setText(
          note,
          "ExoMind point",
          "The 35B ExoMind system stays in the upper-left frontier: high average score with a compact parameter budget."
        );
      } else {
        setText(note, normalizeLabel(point.label), `Average score: ${Number(point.y).toFixed(1)}.`);
      }
    };

    const showArrow = (arrow) => {
      setActiveControl("efficiency");
      showLoupe({
        x: (sx(arrow.from[0]) + sx(arrow.to[0])) / 2,
        y: (sy(arrow.from[1]) + sy(arrow.to[1])) / 2,
        zoom: 1.52,
      });
      setText(
        note,
        arrow.key === "gain" ? "Score gain" : "Parameter-efficiency direction",
        "The zoom uses the original figure itself, so the benchmark graphic remains visually unchanged."
      );
    };

    const showFrontierCluster = () => {
      const points = (data.highlightGroups?.frontier || []).map((key) => pointMap.get(key)).filter(Boolean);
      if (!points.length) return;
      setActiveControl("frontier");
      const bounds = points.reduce(
        (acc, point) => {
          const r = markerRadius(point);
          const x = sx(point.x);
          const y = sy(point.y);
          return {
            left: Math.min(acc.left, x - r),
            right: Math.max(acc.right, x + r),
            top: Math.min(acc.top, y - r),
            bottom: Math.max(acc.bottom, y + r),
          };
        },
        { left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity }
      );
      showLoupe({
        x: (bounds.left + bounds.right) / 2,
        y: (bounds.top + bounds.bottom) / 2,
        zoom: 1.28,
      });
      setText(
        note,
        "Frontier cluster",
        "The right-side cluster collects larger frontier models; hover individual points to inspect their original labels and scores."
      );
    };

    (data.arrows || []).forEach((arrow) => {
      const hit = makeSvg("line", {
        class: "overlay-hit",
        x1: sx(arrow.from[0]),
        y1: sy(arrow.from[1]),
        x2: sx(arrow.to[0]),
        y2: sy(arrow.to[1]),
        stroke: "transparent",
        "stroke-width": 72,
        "stroke-linecap": "round",
        "pointer-events": "stroke",
        tabindex: "0",
        role: "button",
        "data-key": arrow.key,
      });
      addTitle(hit, arrow.label || arrow.key);
      ["mouseenter", "focus", "click"].forEach((eventName) => {
        hit.addEventListener(eventName, () => showArrow(arrow));
      });
      overlay.appendChild(hit);
    });

    panel.points.forEach((point) => {
      const hit = makeSvg("circle", {
        class: "overlay-hit",
        cx: sx(point.x),
        cy: sy(point.y),
        r: markerRadius(point),
        fill: "#000000",
        "pointer-events": "fill",
        tabindex: "0",
        role: "button",
        "data-key": point.key,
      });
      addTitle(hit, `${normalizeLabel(point.label)}: average ${Number(point.y).toFixed(1)}`);
      ["mouseenter", "focus", "click"].forEach((eventName) => {
        hit.addEventListener(eventName, () => showPoint(point.key, point.key === "Ours" ? "exomind" : ""));
      });
      overlay.appendChild(hit);
    });

    container.appendChild(loupe);
    container.appendChild(overlay);
    controls.forEach((control) => {
      const run = () => {
        if (control.dataset.key === "exomind") showPoint("Ours", "exomind");
        if (control.dataset.key === "efficiency") {
          const trend = (data.arrows || []).find((arrow) => arrow.key === "frontier_efficiency") || data.arrows?.[0];
          if (trend) showArrow(trend);
        }
        if (control.dataset.key === "frontier") showFrontierCluster();
      };
      control.addEventListener("mouseenter", run);
      control.addEventListener("focus", run);
      control.addEventListener("click", (event) => {
        event.preventDefault();
        run();
      });
    });

    window.addEventListener("resize", () => {
      if (activeTarget) showLoupe(activeTarget);
    });
    if (image.complete) {
      window.requestAnimationFrame(() => showPoint("Ours", "exomind"));
    } else {
      image.addEventListener("load", () => showPoint("Ours", "exomind"), { once: true });
    }
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

    const clearActive = () => {
      table.querySelectorAll(".is-row-active, .is-column-active").forEach((element) => {
        element.classList.remove("is-row-active", "is-column-active");
      });
    };

    const headerCellsFor = (column) => {
      const top = Array.from(table.tHead.rows[0].cells);
      const leaf = Array.from(table.tHead.rows[1].cells);
      if (column === 0) return [top[0]].filter(Boolean);
      if (column === columnCount - 1) return [top[top.length - 1]].filter(Boolean);
      const group = column <= 4 ? top[1] : top[2];
      return [group, leaf[column - 1]].filter(Boolean);
    };

    const activate = (cell) => {
      clearActive();
      const column = cell.cellIndex;
      cell.parentElement.classList.add("is-row-active");
      rows.forEach((row) => row.cells[column]?.classList.add("is-column-active"));
      headerCellsFor(column).forEach((header) => header.classList.add("is-column-active"));
    };

    rows.forEach((row) => {
      Array.from(row.cells).forEach((cell) => {
        cell.addEventListener("mouseenter", () => activate(cell));
        cell.addEventListener("focus", () => activate(cell));
      });
    });
    table.addEventListener("mouseleave", clearActive);
  };

  renderPerformanceOverlay();
  enhanceBenchmarkTable();
})();
