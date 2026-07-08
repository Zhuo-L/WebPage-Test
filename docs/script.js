(() => {
  const svgNS = "http://www.w3.org/2000/svg";
  const imageSpace = {
    width: 3988,
    height: 1858,
  };

  const makeSvg = (name, attrs = {}) => {
    const element = document.createElementNS(svgNS, name);
    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
    return element;
  };

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

  const renderPerformanceOverlay = () => {
    const container = document.getElementById("performance-chart");
    if (!container) return;

    const note = container.closest(".interactive-figure")?.querySelector(".figure-note");
    const controls = Array.from(container.closest(".interactive-figure")?.querySelectorAll(".figure-control") || []);
    const overlay = makeSvg("svg", {
      class: "chart-overlay",
      viewBox: `0 0 ${imageSpace.width} ${imageSpace.height}`,
      role: "group",
      "aria-label": "Interactive highlights for the benchmark figure",
      focusable: "false",
    });
    const groups = new Map();

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

    const addGroup = (key, elements, title, body) => {
      const items = Array.isArray(elements) ? elements : [elements];
      groups.set(key, { items, title, body });
      items.forEach((element) => overlay.appendChild(element));
    };

    const activateGroup = (key) => {
      const group = groups.get(key);
      if (!group) return;
      clearActive();
      setActiveControl(key);
      group.items.forEach((element) => element.classList.add("is-active"));
      setText(note, group.title, group.body);
    };

    const addHitTarget = (key, element, label) => {
      addTitle(element, label);
      ["mouseenter", "focus", "click"].forEach((eventName) => {
        element.addEventListener(eventName, (event) => {
          if (eventName === "click") event.preventDefault();
          activateGroup(key);
        });
      });
      overlay.appendChild(element);
    };

    addGroup(
      "exomind",
      makeSvg("polygon", {
        class: "chart-emphasis calibrated-highlight exomind-highlight",
        points: starPoints(396, 233, 66, 30),
        "vector-effect": "non-scaling-stroke",
      }),
      "ExoMind point",
      "A 35B agentic system reaches the strongest average region with far fewer parameters."
    );
    addHitTarget(
      "exomind",
      makeSvg("circle", {
        class: "overlay-hit",
        cx: 396,
        cy: 233,
        r: 92,
        fill: "#000000",
        "pointer-events": "fill",
        tabindex: "0",
        role: "button",
      }),
      "Highlight ExoMind point"
    );

    addGroup(
      "efficiency",
      [
        makeSvg("line", {
          class: "chart-emphasis calibrated-highlight trend-highlight trend-vertical",
          x1: 396,
          y1: 310,
          x2: 396,
          y2: 1190,
          "vector-effect": "non-scaling-stroke",
        }),
        makeSvg("line", {
          class: "chart-emphasis calibrated-highlight trend-highlight trend-diagonal",
          x1: 540,
          y1: 255,
          x2: 2750,
          y2: 650,
          "vector-effect": "non-scaling-stroke",
        }),
      ],
      "Parameter-efficiency direction",
      "ExoMind combines the score gain with a shift toward smaller models."
    );
    addHitTarget(
      "efficiency",
      makeSvg("path", {
        class: "overlay-hit",
        d: "M396 310 L396 1190 M540 255 L2750 650",
        fill: "none",
        stroke: "transparent",
        "stroke-width": 86,
        "stroke-linecap": "round",
        "pointer-events": "stroke",
        tabindex: "0",
        role: "button",
      }),
      "Highlight efficiency trend"
    );

    addGroup(
      "frontier",
      makeSvg("rect", {
        class: "chart-emphasis calibrated-highlight cluster-frame",
        x: 2170,
        y: 585,
        width: 930,
        height: 430,
        rx: 20,
        ry: 20,
        "vector-effect": "non-scaling-stroke",
      }),
      "Frontier cluster",
      "Frontier proprietary systems provide the main high-parameter comparison group."
    );
    addHitTarget(
      "frontier",
      makeSvg("rect", {
        class: "overlay-hit",
        x: 2170,
        y: 585,
        width: 930,
        height: 430,
        rx: 20,
        ry: 20,
        fill: "#000000",
        "pointer-events": "fill",
        tabindex: "0",
        role: "button",
      }),
      "Highlight frontier cluster"
    );

    container.appendChild(overlay);
    controls.forEach((control) => {
      const run = () => activateGroup(control.dataset.key);
      control.addEventListener("mouseenter", run);
      control.addEventListener("focus", run);
      control.addEventListener("click", (event) => {
        event.preventDefault();
        run();
      });
    });
    activateGroup("exomind");
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
