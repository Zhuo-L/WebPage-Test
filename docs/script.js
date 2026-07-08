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

  const normalizeLabel = (label) => String(label || "").replace(/\s+/g, " ").trim();

  const setText = (note, title, body) => {
    const noteTitle = note?.querySelector("strong");
    const noteBody = note?.querySelector("p");
    if (noteTitle) noteTitle.textContent = title;
    if (noteBody) noteBody.textContent = body;
  };

  const starPoints = (cx, cy, outerRadius, innerRadius = outerRadius * 0.45) => {
    const points = [];
    for (let i = 0; i < 10; i += 1) {
      const radius = i % 2 === 0 ? outerRadius : innerRadius;
      const angle = -Math.PI / 2 + (Math.PI * i) / 5;
      points.push(`${cx + Math.cos(angle) * radius},${cy + Math.sin(angle) * radius}`);
    }
    return points.join(" ");
  };

  const markerRadius = (point) => {
    if (point.marker === "star") return 56;
    return Math.max(34, Math.min(104, Math.sqrt(Number(point.size || 400)) * 1.9));
  };

  const makeEdgeLine = (name, attrs, color, extraClass = "") =>
    makeSvg(name, {
      ...attrs,
      class: `chart-emphasis chart-edge edge-line ${extraClass}`.trim(),
      fill: "none",
      stroke: color,
      "vector-effect": "non-scaling-stroke",
    });

  const clusterBox = {
    x: 2117,
    y: 538,
    width: 992,
    height: 501,
  };

  const renderPerformanceOverlay = () => {
    const data = window.EXOMIND_PERFORMANCE_DATA;
    const container = document.getElementById("performance-chart");
    const panel = data?.panels?.[0];
    if (!container || !panel) return;

    const note = container.closest(".interactive-figure")?.querySelector(".figure-note");
    const controls = Array.from(container.closest(".interactive-figure")?.querySelectorAll(".figure-control") || []);
    const pointMap = new Map(panel.points.map((point) => [point.key, point]));
    const pointElements = new Map();
    const arrowElements = new Map();
    const clusterElements = [];
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
      "aria-label": "Interactive highlights for the benchmark figure",
      focusable: "false",
    });

    const addTitle = (element, text) => {
      const title = makeSvg("title");
      title.textContent = text;
      element.appendChild(title);
    };

    const clearActive = () => {
      overlay.querySelectorAll(".is-active").forEach((element) => element.classList.remove("is-active"));
    };

    const setActiveControl = (key) => {
      controls.forEach((control) => control.classList.toggle("is-active", control.dataset.key === key));
    };

    const activatePoint = (key, controlKey = "") => {
      const point = pointMap.get(key);
      if (!point) return;
      clearActive();
      setActiveControl(controlKey);
      (pointElements.get(key) || []).forEach((element) => element.classList.add("is-active"));
      if (point.key === "Ours") {
        setText(note, "ExoMind point", "A 35B agentic system reaches the strongest average region with far fewer parameters.");
      } else {
        setText(note, normalizeLabel(point.label), `Average score ${Number(point.y).toFixed(1)}`);
      }
    };

    const activateArrow = (arrow) => {
      clearActive();
      setActiveControl("efficiency");
      (arrowElements.get(arrow.key) || []).forEach((element) => element.classList.add("is-active"));
      setText(
        note,
        arrow.key === "gain" ? "Score gain" : "Parameter-efficiency direction",
        "The performance frontier moves toward smaller models with stronger scientific intelligence."
      );
    };

    const activateTrend = () => {
      clearActive();
      setActiveControl("efficiency");
      (data.highlightGroups?.trend || [])
        .flatMap((key) => arrowElements.get(key) || [])
        .forEach((element) => element.classList.add("is-active"));
      setText(
        note,
        "Parameter-efficiency direction",
        "ExoMind combines the score gain with a shift toward smaller models."
      );
    };

    const activateFrontier = () => {
      clearActive();
      setActiveControl("frontier");
      clusterElements.forEach((element) => element.classList.add("is-active"));
      (data.highlightGroups?.frontier || []).forEach((key) => {
        (pointElements.get(key) || []).forEach((element) => element.classList.add("is-active"));
      });
      setText(note, "Frontier cluster", "Frontier proprietary systems provide the main high-parameter comparison group.");
    };

    const clusterFrame = makeSvg("rect", {
      class: "chart-emphasis cluster-frame",
      x: clusterBox.x,
      y: clusterBox.y,
      width: clusterBox.width,
      height: clusterBox.height,
      rx: 22,
      ry: 22,
      fill: "none",
      "vector-effect": "non-scaling-stroke",
    });
    overlay.appendChild(clusterFrame);
    clusterElements.push(clusterFrame);

    (data.arrows || []).forEach((arrow) => {
      const x1 = sx(arrow.from[0]);
      const y1 = sy(arrow.from[1]);
      const x2 = sx(arrow.to[0]);
      const y2 = sy(arrow.to[1]);
      const emphasis = makeEdgeLine(
        "line",
        {
          x1,
          y1,
          x2,
          y2,
          "stroke-linecap": "round",
        },
        "#e31a1c",
        "is-arrow"
      );
      const hit = makeSvg("line", {
        class: "overlay-hit",
        x1,
        y1,
        x2,
        y2,
        stroke: "transparent",
        "stroke-width": 62,
        "stroke-linecap": "round",
        "pointer-events": "stroke",
        tabindex: "0",
        role: "button",
      });
      addTitle(hit, arrow.label || arrow.key);
      ["mouseenter", "focus", "click"].forEach((eventName) => {
        hit.addEventListener(eventName, () => activateArrow(arrow));
      });
      overlay.appendChild(emphasis);
      overlay.appendChild(hit);
      arrowElements.set(arrow.key, [emphasis]);
    });

    panel.points.forEach((point) => {
      const cx = sx(point.x);
      const cy = sy(point.y);
      const r = markerRadius(point);
      const emphasis =
        point.marker === "star"
          ? makeEdgeLine(
              "polygon",
              { points: starPoints(cx, cy, r) },
              point.color || "#e31a1c",
              "is-point is-star"
            )
          : makeEdgeLine(
              "circle",
              { cx, cy, r },
              point.color || "#50e2d0",
              "is-point"
            );
      const hit = makeSvg("circle", {
        class: "overlay-hit",
        cx,
        cy,
        r: Math.max(r + 20, 50),
        fill: "#000000",
        "pointer-events": "fill",
        tabindex: "0",
        role: "button",
      });
      addTitle(hit, `${normalizeLabel(point.label)} average ${Number(point.y).toFixed(1)}`);
      ["mouseenter", "focus", "click"].forEach((eventName) => {
        hit.addEventListener(eventName, () => activatePoint(point.key, point.key === "Ours" ? "exomind" : ""));
      });
      overlay.appendChild(emphasis);
      overlay.appendChild(hit);
      pointElements.set(point.key, [emphasis]);
    });

    container.appendChild(overlay);
    controls.forEach((control) => {
      const run = () => {
        if (control.dataset.key === "exomind") activatePoint("Ours", "exomind");
        if (control.dataset.key === "efficiency") activateTrend();
        if (control.dataset.key === "frontier") activateFrontier();
      };
      control.addEventListener("mouseenter", run);
      control.addEventListener("focus", run);
      control.addEventListener("click", (event) => {
        event.preventDefault();
        run();
      });
    });
    activatePoint("Ours", "exomind");
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

  renderPerformanceOverlay();
  enhanceBenchmarkTable();
})();
