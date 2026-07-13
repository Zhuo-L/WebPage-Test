(() => {
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const empty = (element) => {
    while (element.firstChild) element.removeChild(element.firstChild);
  };

  const createChartInteraction = (container, points) => {
    const hotspotLayer = container ? container.querySelector(".chart-hotspots") : null;
    const tooltip = container ? container.querySelector(".chart-tooltip") : null;
    if (!container || !hotspotLayer || !tooltip || !points.length) return;

    const buttons = [];

    const clear = () => {
      buttons.forEach((button) => button.classList.remove("is-active"));
      container.classList.remove("has-active");
      tooltip.classList.remove("is-visible", "is-below");
      empty(tooltip);
    };

    const activate = (button, point) => {
      buttons.forEach((item) => item.classList.toggle("is-active", item === button));
      container.classList.add("has-active");

      const title = document.createTextNode(point.name);
      const detail = document.createElement("span");
      detail.textContent = point.detail;
      empty(tooltip);
      tooltip.appendChild(title);
      tooltip.appendChild(detail);
      tooltip.style.left = `${clamp(point.x, 14, 86)}%`;
      tooltip.style.top = `${point.y}%`;
      tooltip.classList.toggle("is-below", point.y < 18);
      tooltip.classList.add("is-visible");
    };

    points.forEach((point) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "chart-point";
      button.setAttribute("aria-label", `${point.name}. ${point.detail}`);
      button.style.left = `${point.x}%`;
      button.style.top = `${point.y}%`;
      button.style.setProperty("--point-color", point.color || "#50e2d0");
      button.style.setProperty("--point-size", `${point.size || 34}px`);
      button.style.width = `${point.size || 34}px`;
      button.style.height = `${point.size || 34}px`;
      button.addEventListener("pointerenter", () => activate(button, point));
      button.addEventListener("focus", () => activate(button, point));
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        activate(button, point);
      });
      buttons.push(button);
      hotspotLayer.appendChild(button);
    });

    container.addEventListener("pointerleave", () => {
      if (!buttons.includes(document.activeElement)) clear();
    });
    container.addEventListener("click", (event) => {
      if (!event.target.classList || !event.target.classList.contains("chart-point")) clear();
    });
    container.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        clear();
        if (typeof container.focus === "function") container.focus();
      }
    });
  };

  const enhancePerformanceChart = () => {
    const data = window.EXOMIND_PERFORMANCE_DATA;
    const panel = data && data.panels
      ? data.panels.find((item) => item.id === "avg")
      : null;
    if (!panel) return;

    const plot = {
      left: 5.57,
      top: 8.82,
      width: 74.32,
      height: 69.7,
      xmin: 0,
      xmax: 2.2,
      ymin: 30,
      ymax: 70,
    };

    const points = panel.points.map((point) => ({
      name: point.label.replace(/\n/g, " "),
      detail: `Average score ${point.y.toFixed(1)}`,
      x: plot.left + ((point.x - plot.xmin) / (plot.xmax - plot.xmin)) * plot.width,
      y: plot.top + ((plot.ymax - point.y) / (plot.ymax - plot.ymin)) * plot.height,
      color: point.color,
      size: clamp(18 + Math.sqrt(point.size) * 0.5, 28, 48),
    }));

    createChartInteraction(document.querySelector("#performance-chart"), points);
  };

  const modelAbbreviation = (model) => {
    if (model.isOurs) return "Exo";
    return {
      OpenAI: "GPT",
      Google: "Gem",
      Claude: "Cla",
      DeepSeek: "DS",
      Qwen: "Qw",
      Kimi: "Kimi",
      GLM: "GLM",
      MiniMax: "MM",
      "Shanghai AI Lab": "S2",
    }[model.provider] || model.provider.slice(0, 3);
  };

  const setReadout = (readout, model, score) => {
    const name = document.createElement("strong");
    name.textContent = model.name;
    empty(readout);
    readout.appendChild(name);
    readout.appendChild(document.createTextNode(`  ${score.toFixed(1)}`));
  };

  const renderBenchmarkBars = () => {
    const root = document.querySelector("#benchmark-bars");
    const data = window.EXOMIND_BENCHMARK_DATA;
    if (!root || !data || !data.datasets || !data.datasets.length || !data.models || !data.models.length) return;

    data.datasets.forEach((dataset) => {
      const models = data.models.filter((model) => Number.isFinite(model.scores[dataset.id]));
      const ours = models.find((model) => model.isOurs) || models[0];

      const panel = document.createElement("article");
      panel.className = "benchmark-panel";

      const header = document.createElement("div");
      header.className = "benchmark-panel-head";
      const title = document.createElement("h3");
      title.textContent = dataset.label;
      const readout = document.createElement("span");
      setReadout(readout, ours, ours.scores[dataset.id]);
      header.appendChild(title);
      header.appendChild(readout);

      const scroll = document.createElement("div");
      scroll.className = "bar-scroll";
      const plot = document.createElement("div");
      plot.className = "bar-plot";

      const labels = document.createElement("div");
      labels.className = "bar-axis-labels";
      [100, 75, 50, 25, 0].forEach((value) => {
        const label = document.createElement("span");
        label.textContent = value;
        labels.appendChild(label);
      });

      const bars = document.createElement("div");
      bars.className = "bars";
      const barButtons = [];

      const clear = () => {
        bars.classList.remove("has-active");
        barButtons.forEach((button) => button.classList.remove("is-active"));
        setReadout(readout, ours, ours.scores[dataset.id]);
      };

      models.forEach((model) => {
        const score = model.scores[dataset.id];
        const button = document.createElement("button");
        button.type = "button";
        button.className = `benchmark-bar${model.isOurs ? " is-ours" : ""}`;
        button.title = `${model.name}: ${score.toFixed(1)}`;
        button.setAttribute("aria-label", `${model.name}, ${dataset.label}, ${score.toFixed(1)}`);
        button.style.setProperty("--bar-height", `${clamp(score, 0, 100)}%`);
        button.style.setProperty("--bar-color", model.color);

        const fill = document.createElement("span");
        fill.className = "bar-fill";
        fill.style.height = `${clamp(score, 0, 100)}%`;
        fill.style.backgroundColor = model.color;
        const value = document.createElement("span");
        value.className = "bar-value";
        value.textContent = score.toFixed(1);
        value.style.bottom = `calc(${clamp(score, 0, 100)}% + 5px)`;
        const abbreviation = document.createElement("span");
        abbreviation.className = "bar-abbr";
        abbreviation.textContent = modelAbbreviation(model);
        button.appendChild(fill);
        button.appendChild(value);
        button.appendChild(abbreviation);

        const activate = () => {
          bars.classList.add("has-active");
          barButtons.forEach((item) => item.classList.toggle("is-active", item === button));
          setReadout(readout, model, score);
        };

        button.addEventListener("pointerenter", activate);
        button.addEventListener("focus", activate);
        button.addEventListener("click", activate);
        barButtons.push(button);
        bars.appendChild(button);
      });

      bars.addEventListener("pointerleave", () => {
        if (!barButtons.includes(document.activeElement)) clear();
      });
      panel.addEventListener("keydown", (event) => {
        if (event.key === "Escape") clear();
      });

      plot.appendChild(labels);
      plot.appendChild(bars);
      scroll.appendChild(plot);
      panel.appendChild(header);
      panel.appendChild(scroll);
      root.appendChild(panel);
    });
  };

  const enhanceIkpChart = () => {
    const points = [
      { name: "ExoMind", detail: "IKP accuracy 56.0% · 35B actual, nearly 1T equivalent", x: 9.75, y: 41.5, color: "#e31a1c", size: 42 },
      { name: "Qwen3.5-35B-A3B", detail: "IKP accuracy 37.5% · 35B", x: 9.75, y: 68.3, color: "#ab68e6", size: 28 },
      { name: "Qwen3.5-122B-A10B", detail: "IKP accuracy 48.3% · 122B", x: 23.85, y: 52.6, color: "#ab68e6", size: 30 },
      { name: "MiniMax-M2.7", detail: "IKP accuracy 40.8% · 229B", x: 30.85, y: 63.2, color: "#f03365", size: 34 },
      { name: "Qwen3.5-397B-A17B", detail: "IKP accuracy 48.9% · 397B", x: 37.0, y: 51.9, color: "#ab68e6", size: 34 },
      { name: "Qwen3.6-Plus", detail: "IKP accuracy 53.3% · 524B", x: 39.95, y: 45.4, color: "#ab68e6", size: 34 },
      { name: "Claude-Opus-4.8", detail: "IKP accuracy 53.7% · 572B", x: 41.2, y: 44.7, color: "#ee822f", size: 34 },
      { name: "Qwen3.7-Max", detail: "IKP accuracy 55.8% · 685B", x: 43.0, y: 42.0, color: "#ab68e6", size: 36 },
      { name: "GLM-5", detail: "IKP accuracy 57.1% · 744B", x: 44.0, y: 39.0, color: "#9da3aa", size: 36 },
      { name: "Kimi-K2.6", detail: "IKP accuracy 62.0% · 1.0T", x: 47.8, y: 32.2, color: "#69aeff", size: 38 },
      { name: "DeepSeek-V4-Pro (Max)", detail: "IKP accuracy 61.0% · 1.6T", x: 52.5, y: 34.0, color: "#4f6aef", size: 38 },
      { name: "GPT-5.4 (xhigh)", detail: "IKP accuracy 61.9% · 2.2T", x: 56.2, y: 32.6, color: "#0ca982", size: 38 },
      { name: "Gemini-3.5-Flash-Thinking", detail: "IKP accuracy 69.0% · 6.6T", x: 68.4, y: 22.2, color: "#fabc05", size: 42 },
      { name: "GPT-5.5 (xhigh)", detail: "IKP accuracy 71.2% · 9.7T", x: 72.8, y: 19.2, color: "#0ca982", size: 44 },
    ];

    createChartInteraction(document.querySelector("#ikp-chart"), points);
  };

  const enhanceFigureLightbox = () => {
    const dialog = document.querySelector("#figure-lightbox");
    const dialogImage = dialog ? dialog.querySelector("img") : null;
    const scroll = dialog ? dialog.querySelector(".lightbox-scroll") : null;
    const closeButton = dialog ? dialog.querySelector(".lightbox-close") : null;
    const triggers = document.querySelectorAll(".zoomable-figure[data-figure]");
    if (!dialog || !dialogImage || !scroll || !closeButton) return;

    const close = () => {
      if (dialog.open && typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    };

    Array.prototype.forEach.call(triggers, (trigger) => {
      trigger.addEventListener("click", () => {
        const sourceImage = trigger.querySelector("img");
        dialogImage.src = trigger.dataset.figure;
        dialogImage.alt = (sourceImage && sourceImage.alt) || "Expanded figure";
        scroll.classList.add("is-fit");
        if (typeof dialog.showModal === "function") dialog.showModal();
        else dialog.setAttribute("open", "");
      });
    });

    closeButton.addEventListener("click", close);
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) close();
    });
    scroll.addEventListener("click", () => scroll.classList.toggle("is-fit"));
    dialog.addEventListener("close", () => {
      dialogImage.src = "";
      dialogImage.alt = "";
    });
  };

  enhancePerformanceChart();
  renderBenchmarkBars();
  enhanceIkpChart();
  enhanceFigureLightbox();
})();
