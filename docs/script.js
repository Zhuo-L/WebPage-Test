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

  const setText = (note, title, body) => {
    const noteTitle = note?.querySelector("strong");
    const noteBody = note?.querySelector("p");
    if (noteTitle) noteTitle.textContent = title;
    if (noteBody) noteBody.textContent = body;
  };

  const normalizeLabel = (label) => String(label || "").replace(/\s+/g, " ").trim();

  const markerRadius = (point) => {
    if (point.marker === "star") return 66;
    return Math.max(34, Math.min(128, Math.sqrt(Number(point.size || 400)) * 2.12));
  };

  const renderPerformanceOverlay = () => {
    const data = window.EXOMIND_PERFORMANCE_DATA;
    const container = document.getElementById("performance-chart");
    const panel = data?.panels?.[0];
    if (!container || !panel) return;

    const note = container.closest(".interactive-figure")?.querySelector(".figure-note");
    const controls = Array.from(container.closest(".interactive-figure")?.querySelectorAll(".figure-control") || []);
    const pointElements = new Map();
    const arrowElements = new Map();
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
      "aria-label": "Interactive highlights for the benchmark figure",
      focusable: "false",
    });

    const addTitle = (element, text) => {
      const title = makeSvg("title");
      title.textContent = text;
      element.appendChild(title);
    };

    const addActive = (items) => items.forEach((element) => element.classList.add("overlay-active"));
    const clearActive = () => {
      overlay.querySelectorAll(".overlay-active").forEach((element) => element.classList.remove("overlay-active"));
    };
    const activatePoint = (key) => addActive(pointElements.get(key) || []);
    const activateArrow = (key) => addActive(arrowElements.get(key) || []);

    const activate = (key, type = "point") => {
      clearActive();
      controls.forEach((control) => {
        const selected =
          control.dataset.key === key ||
          (control.dataset.key === "efficiency" && (key === "trend" || type === "arrow"));
        control.classList.toggle("is-active", selected);
      });

      if (key === "exomind") {
        (data.highlightGroups?.exomind || ["Ours"]).forEach(activatePoint);
        setText(
          note,
          "ExoMind point",
          "The 35B ExoMind system stays in the upper-left frontier: high average score with a compact parameter budget."
        );
        return;
      }

      if (key === "frontier") {
        (data.highlightGroups?.frontier || []).forEach(activatePoint);
        addActive(Array.from(overlay.querySelectorAll("[data-overlay='frontier-cluster']")));
        setText(
          note,
          "Frontier cluster",
          "The high-parameter frontier models cluster on the right side of the original figure; hover an individual model for its score."
        );
        return;
      }

      if (key === "efficiency" || key === "trend") {
        (data.highlightGroups?.trend || []).forEach(activateArrow);
        setText(
          note,
          "Efficiency trend",
          "The original red guides emphasize the movement from larger frontier models toward the compact ExoMind operating point."
        );
        return;
      }

      if (type === "arrow") {
        activateArrow(key);
        setText(
          note,
          key === "gain" ? "Score gain" : "Parameter-efficiency direction",
          "This highlight follows the red guide already drawn in the original figure."
        );
        return;
      }

      const point = pointMap.get(key);
      if (point) {
        activatePoint(key);
        setText(note, normalizeLabel(point.label), `Average score: ${Number(point.y).toFixed(1)}.`);
      }
    };

    const clusterPoints = (data.highlightGroups?.frontier || [])
      .map((key) => pointMap.get(key))
      .filter(Boolean);
    if (clusterPoints.length) {
      const bounds = clusterPoints.reduce(
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
      overlay.appendChild(
        makeSvg("rect", {
          class: "overlay-cluster",
          x: bounds.left - 46,
          y: bounds.top - 44,
          width: bounds.right - bounds.left + 92,
          height: bounds.bottom - bounds.top + 88,
          rx: 28,
          "data-overlay": "frontier-cluster",
        })
      );
    }

    (data.arrows || []).forEach((arrow) => {
      const x1 = sx(arrow.from[0]);
      const y1 = sy(arrow.from[1]);
      const x2 = sx(arrow.to[0]);
      const y2 = sy(arrow.to[1]);
      const guide = makeSvg("line", {
        class: "overlay-guide",
        x1,
        y1,
        x2,
        y2,
        "data-key": arrow.key,
      });
      const hit = makeSvg("line", {
        class: "overlay-hit",
        x1,
        y1,
        x2,
        y2,
        stroke: "transparent",
        "stroke-width": 64,
        "stroke-linecap": "round",
        tabindex: "0",
        role: "button",
        "data-key": arrow.key,
      });
      addTitle(hit, arrow.label || arrow.key);
      ["mouseenter", "focus", "click"].forEach((eventName) => {
        hit.addEventListener(eventName, () => activate(arrow.key, "arrow"));
      });
      overlay.appendChild(guide);
      overlay.appendChild(hit);
      arrowElements.set(arrow.key, [guide]);
    });

    panel.points.forEach((point) => {
      const cx = sx(point.x);
      const cy = sy(point.y);
      const r = markerRadius(point);
      const halo = makeSvg("circle", {
        class: "overlay-halo",
        cx,
        cy,
        r: r + 15,
        "data-key": point.key,
      });
      const ring = makeSvg("circle", {
        class: "overlay-ring",
        cx,
        cy,
        r: r + 6,
        stroke: point.color || "#ff6f9f",
        "data-key": point.key,
      });
      const hit = makeSvg("circle", {
        class: "overlay-hit",
        cx,
        cy,
        r: Math.max(r + 22, 48),
        fill: "transparent",
        tabindex: "0",
        role: "button",
        "data-key": point.key,
      });
      addTitle(hit, `${normalizeLabel(point.label)}: average ${Number(point.y).toFixed(1)}`);
      ["mouseenter", "focus", "click"].forEach((eventName) => {
        hit.addEventListener(eventName, () => activate(point.key === "Ours" ? "exomind" : point.key));
      });
      overlay.appendChild(halo);
      overlay.appendChild(ring);
      overlay.appendChild(hit);
      pointElements.set(point.key, [halo, ring]);
    });

    container.appendChild(overlay);
    container.classList.add("has-overlay");
    controls.forEach((control) => {
      const run = () => activate(control.dataset.key);
      control.addEventListener("mouseenter", run);
      control.addEventListener("focus", run);
      control.addEventListener("click", (event) => {
        event.preventDefault();
        run();
      });
    });
    activate("exomind");
  };

  renderPerformanceOverlay();
})();
