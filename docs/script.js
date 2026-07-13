(() => {
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const toArray = (collection) => Array.prototype.slice.call(collection || []);
  const empty = (element) => {
    while (element && element.firstChild) element.removeChild(element.firstChild);
  };

  const createChartInteraction = (container, config) => {
    const hotspotLayer = container ? container.querySelector(".chart-hotspots") : null;
    const tooltip = container ? container.querySelector(".chart-tooltip") : null;
    const image = container ? container.querySelector("img") : null;
    const points = config ? config.points : null;
    if (
      !container ||
      !hotspotLayer ||
      !tooltip ||
      !image ||
      !config.sourceWidth ||
      !config.sourceHeight ||
      !points ||
      !points.length
    ) return;

    const buttons = [];
    const coarsePointer = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;

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
      tooltip.style.left = `${clamp((point.sourceX / config.sourceWidth) * 100, 14, 86)}%`;
      tooltip.style.top = `${(point.sourceY / config.sourceHeight) * 100}%`;
      tooltip.classList.toggle("is-below", point.sourceY / config.sourceHeight < 0.18);
      tooltip.classList.add("is-visible");
    };

    points.forEach((point) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "chart-point";
      button.setAttribute("aria-label", `${point.name}. ${point.detail}`);
      button.style.left = `${(point.sourceX / config.sourceWidth) * 100}%`;
      button.style.top = `${(point.sourceY / config.sourceHeight) * 100}%`;
      button.style.setProperty("--point-color", point.color || "#df2f2f");
      button.addEventListener("mouseenter", () => activate(button, point));
      button.addEventListener("focus", () => activate(button, point));
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        activate(button, point);
      });
      buttons.push(button);
      hotspotLayer.appendChild(button);
    });

    const updateGeometry = () => {
      const renderedWidth = image.getBoundingClientRect().width || container.clientWidth;
      const scale = renderedWidth / config.sourceWidth;
      const minimumHitSize = coarsePointer ? 44 : 32;

      buttons.forEach((button, index) => {
        const markerSize = Math.max(10, points[index].sourceDiameter * scale + 4);
        const hitSize = Math.max(minimumHitSize, markerSize + 10);
        button.style.setProperty("--marker-size", `${markerSize}px`);
        button.style.setProperty("--hit-size", `${hitSize}px`);
      });
    };

    if ("ResizeObserver" in window) {
      const resizeObserver = new ResizeObserver(updateGeometry);
      resizeObserver.observe(container);
    }
    image.addEventListener("load", updateGeometry);
    window.addEventListener("resize", updateGeometry, { passive: true });
    updateGeometry();

    container.addEventListener("mouseleave", () => {
      if (!buttons.includes(document.activeElement)) clear();
    });
    container.addEventListener("click", (event) => {
      if (!event.target.classList || !event.target.classList.contains("chart-point")) clear();
    });
    container.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        clear();
        container.focus();
      }
    });
  };

  const enhancePerformanceChart = () => {
    const data = window.EXOMIND_PERFORMANCE_DATA;
    const panel = data && data.panels
      ? data.panels.find((item) => item.id === "avg")
      : null;
    if (!panel) return;

    const source = {
      width: 3988,
      height: 1858,
      plotLeft: 218,
      plotRight: 3098,
      plotTop: 160,
      plotBottom: 1420,
    };

    const markerDiameters = {
      Ours: 102,
      "GPT-5.5 (xhigh)": 208,
      "Gemini-3.1-Pro-Preview": 208,
      "Gemini-3.5-Flash-Thinking": 204,
      "Claude-Opus-4.8-Thinking": 146,
      "Qwen3.7-Max": 128,
      "DeepSeek-V4-Pro (Max)": 154,
      "DeepSeek-V4-Flash (Max)": 102,
      "Kimi-K2.6": 150,
      "GLM-5.2": 132,
      "MiniMax-M3": 112,
      "Qwen3.5-397B-A17B": 108,
      "Qwen3.5-122B-A10B": 90,
      "Qwen3.5-35B-A3B": 84,
      "Gemma-4-31B": 84,
      "Intern-S2-Preview": 84,
    };

    const points = panel.points.map((point) => ({
      name: point.label.replace(/\n/g, " "),
      detail: `Average score ${point.y.toFixed(1)}`,
      sourceX: source.plotLeft + (point.x / 2.2) * (source.plotRight - source.plotLeft),
      sourceY: source.plotTop + ((70 - point.y) / 40) * (source.plotBottom - source.plotTop),
      color: point.color,
      sourceDiameter: markerDiameters[point.key] || 90,
    }));

    createChartInteraction(document.querySelector("#performance-chart"), {
      sourceWidth: source.width,
      sourceHeight: source.height,
      points,
    });
  };

  const formatScore = (score) => Number(score).toFixed(1);

  const renderBenchmarkExplorer = () => {
    const tabsRoot = document.querySelector("#benchmark-tabs");
    const summaryRoot = document.querySelector("#benchmark-summary");
    const rankingRoot = document.querySelector("#benchmark-ranking");
    const data = window.EXOMIND_BENCHMARK_DATA;
    if (
      !tabsRoot ||
      !summaryRoot ||
      !rankingRoot ||
      !data ||
      !data.datasets ||
      !data.datasets.length ||
      !data.models ||
      !data.models.length
    ) return;

    const datasets = data.datasets.concat(data.general ? [data.general] : []);
    const tabButtons = [];
    let activeIndex = 0;

    const renderSummary = (dataset, ours, rank, total) => {
      empty(summaryRoot);

      const context = document.createElement("div");
      const domain = document.createElement("p");
      const title = document.createElement("h3");
      domain.className = "summary-domain";
      domain.textContent = dataset.domain;
      title.className = "summary-title";
      title.textContent = dataset.label;
      context.appendChild(domain);
      context.appendChild(title);

      const result = document.createElement("p");
      const score = document.createElement("strong");
      result.className = "summary-result";
      score.textContent = formatScore(ours.scores[dataset.id]);
      result.appendChild(score);
      result.appendChild(document.createTextNode(` ExoMind score · Rank ${rank} of ${total}`));

      summaryRoot.appendChild(context);
      summaryRoot.appendChild(result);
    };

    const renderGeneralSummary = (dataset) => {
      empty(summaryRoot);

      const context = document.createElement("div");
      const domain = document.createElement("p");
      const title = document.createElement("h3");
      const result = document.createElement("p");
      const count = document.createElement("strong");

      domain.className = "summary-domain";
      domain.textContent = dataset.domain;
      title.className = "summary-title";
      title.textContent = "General intelligence benchmarks";
      result.className = "summary-result";
      count.textContent = `${dataset.series.length} / ${dataset.series.length}`;
      result.appendChild(count);
      result.appendChild(document.createTextNode(" benchmarks improved over Base 35B"));
      context.appendChild(domain);
      context.appendChild(title);
      summaryRoot.appendChild(context);
      summaryRoot.appendChild(result);
    };

    const renderRanking = (dataset) => {
      const models = data.models
        .filter((model) => Number.isFinite(model.scores[dataset.id]))
        .slice()
        .sort((a, b) => b.scores[dataset.id] - a.scores[dataset.id]);
      const ours = models.find((model) => model.isOurs) || models[0];
      const ourRank = models.indexOf(ours) + 1;

      renderSummary(dataset, ours, ourRank, models.length);
      empty(rankingRoot);
      rankingRoot.classList.remove("is-general");
      rankingRoot.setAttribute("aria-labelledby", `benchmark-tab-${dataset.id}`);

      models.forEach((model, index) => {
        const score = model.scores[dataset.id];
        const row = document.createElement("div");
        const rank = document.createElement("span");
        const modelCell = document.createElement("span");
        const name = document.createElement("span");
        const provider = document.createElement("span");
        const track = document.createElement("span");
        const fill = document.createElement("span");
        const value = document.createElement("span");

        row.className = `ranking-row${model.isOurs ? " is-ours" : ""}`;
        row.setAttribute(
          "aria-label",
          `${index + 1}. ${model.name}, ${formatScore(score)} on ${dataset.label}`
        );
        rank.className = "ranking-rank";
        rank.textContent = index + 1;
        modelCell.className = "ranking-model";
        name.className = "model-name";
        name.textContent = model.name;
        provider.className = "model-provider";
        provider.textContent = model.provider;
        track.className = "ranking-track";
        fill.className = "ranking-fill";
        fill.style.setProperty("--score-width", `${clamp(score, 0, 100)}%`);
        fill.style.width = `${clamp(score, 0, 100)}%`;
        value.className = "ranking-score";
        value.textContent = formatScore(score);

        modelCell.appendChild(name);
        modelCell.appendChild(provider);
        track.appendChild(fill);
        row.appendChild(rank);
        row.appendChild(modelCell);
        row.appendChild(track);
        row.appendChild(value);
        rankingRoot.appendChild(row);
      });
    };

    const renderGeneralComparison = (dataset) => {
      renderGeneralSummary(dataset);
      empty(rankingRoot);
      rankingRoot.classList.add("is-general");
      rankingRoot.setAttribute("aria-labelledby", `benchmark-tab-${dataset.id}`);

      dataset.series.forEach((benchmark) => {
        const row = document.createElement("div");
        const name = document.createElement("span");
        const bars = document.createElement("div");

        row.className = "general-row";
        row.setAttribute(
          "aria-label",
          `${benchmark.label}: Base 35B ${formatScore(benchmark.base)}, ExoMind ${formatScore(benchmark.exomind)}`
        );
        name.className = "general-name";
        name.textContent = benchmark.label;
        bars.className = "general-bars";

        [
          { label: "Base 35B", value: benchmark.base, ours: false },
          { label: "ExoMind", value: benchmark.exomind, ours: true },
        ].forEach((series) => {
          const seriesRow = document.createElement("div");
          const label = document.createElement("span");
          const track = document.createElement("span");
          const fill = document.createElement("span");
          const value = document.createElement("span");

          seriesRow.className = `general-series${series.ours ? " is-exomind" : ""}`;
          label.className = "general-series-label";
          label.textContent = series.label;
          track.className = "general-series-track";
          fill.className = "general-series-fill";
          fill.style.width = `${clamp(series.value, 0, 100)}%`;
          value.className = "general-series-value";
          value.textContent = formatScore(series.value);
          track.appendChild(fill);
          seriesRow.appendChild(label);
          seriesRow.appendChild(track);
          seriesRow.appendChild(value);
          bars.appendChild(seriesRow);
        });

        row.appendChild(name);
        row.appendChild(bars);
        rankingRoot.appendChild(row);
      });
    };

    const renderDataset = (dataset) => {
      if (dataset.id === "general") renderGeneralComparison(dataset);
      else renderRanking(dataset);
    };

    const activateTab = (index, moveFocus) => {
      activeIndex = (index + datasets.length) % datasets.length;
      tabButtons.forEach((button, buttonIndex) => {
        const selected = buttonIndex === activeIndex;
        button.setAttribute("aria-selected", selected ? "true" : "false");
        button.tabIndex = selected ? 0 : -1;
      });
      renderDataset(datasets[activeIndex]);
      if (moveFocus) tabButtons[activeIndex].focus();
      const activeButton = tabButtons[activeIndex];
      const targetScroll = activeButton.offsetLeft - tabsRoot.clientWidth + activeButton.offsetWidth + 18;
      tabsRoot.scrollLeft = activeIndex === 0 ? 0 : Math.max(0, targetScroll);
    };

    datasets.forEach((dataset, index) => {
      const button = document.createElement("button");
      button.id = `benchmark-tab-${dataset.id}`;
      button.type = "button";
      button.role = "tab";
      button.textContent = dataset.label;
      button.setAttribute("aria-controls", "benchmark-ranking");
      button.setAttribute("aria-selected", index === 0 ? "true" : "false");
      button.tabIndex = index === 0 ? 0 : -1;
      button.addEventListener("click", () => activateTab(index, false));
      button.addEventListener("keydown", (event) => {
        if (event.key === "ArrowRight") {
          event.preventDefault();
          activateTab(activeIndex + 1, true);
        } else if (event.key === "ArrowLeft") {
          event.preventDefault();
          activateTab(activeIndex - 1, true);
        } else if (event.key === "Home") {
          event.preventDefault();
          activateTab(0, true);
        } else if (event.key === "End") {
          event.preventDefault();
          activateTab(datasets.length - 1, true);
        }
      });
      tabButtons.push(button);
      tabsRoot.appendChild(button);
    });

    activateTab(0, false);
  };

  const enhanceTabGroups = () => {
    const groups = toArray(document.querySelectorAll(".evidence-viewer, [data-tab-group]"));

    groups.forEach((group) => {
      const buttons = toArray(group.querySelectorAll("[role='tab']"));
      const panels = toArray(group.querySelectorAll("[role='tabpanel']"));
      if (!buttons.length || !panels.length) return;

      let activeIndex = Math.max(
        0,
        buttons.findIndex((button) => button.getAttribute("aria-selected") === "true")
      );

      const activate = (index, moveFocus) => {
        activeIndex = (index + buttons.length) % buttons.length;
        buttons.forEach((button, buttonIndex) => {
          const selected = buttonIndex === activeIndex;
          button.setAttribute("aria-selected", selected ? "true" : "false");
          button.tabIndex = selected ? 0 : -1;
        });
        panels.forEach((panel) => {
          panel.hidden = panel.id !== buttons[activeIndex].getAttribute("aria-controls");
        });
        if (moveFocus) buttons[activeIndex].focus();
      };

      buttons.forEach((button, index) => {
        button.addEventListener("click", () => activate(index, false));
        button.addEventListener("keydown", (event) => {
          if (event.key === "ArrowRight") {
            event.preventDefault();
            activate(activeIndex + 1, true);
          } else if (event.key === "ArrowLeft") {
            event.preventDefault();
            activate(activeIndex - 1, true);
          } else if (event.key === "Home") {
            event.preventDefault();
            activate(0, true);
          } else if (event.key === "End") {
            event.preventDefault();
            activate(buttons.length - 1, true);
          }
        });
      });

      activate(activeIndex, false);
    });
  };

  const enhanceIkpChart = () => {
    const points = [
      { name: "ExoMind", detail: "IKP accuracy 56.0% · 35B actual, nearly 1T equivalent", sourceX: 409, sourceY: 837, sourceDiameter: 102, color: "#e31a1c" },
      { name: "Qwen3.5-35B-A3B", detail: "IKP accuracy 37.4% · 35B", sourceX: 409, sourceY: 1369, sourceDiameter: 28, color: "#ab68e6" },
      { name: "Qwen3.5-122B-A10B", detail: "IKP accuracy 48.3% · 122B", sourceX: 991, sourceY: 1058, sourceDiameter: 52, color: "#ab68e6" },
      { name: "MiniMax-M2.7", detail: "IKP accuracy 40.9% · 229B", sourceX: 1283, sourceY: 1270, sourceDiameter: 62, color: "#f03365" },
      { name: "DeepSeek-V4-Flash (Max)", detail: "IKP accuracy 56.3%", sourceX: 1383, sourceY: 829, sourceDiameter: 66, color: "#4f6aef" },
      { name: "Qwen3.5-397B-A17B", detail: "IKP accuracy 48.9% · 397B", sourceX: 1539, sourceY: 1041, sourceDiameter: 72, color: "#ab68e6" },
      { name: "Qwen3.6-Plus", detail: "IKP accuracy 53.3% · 524B", sourceX: 1668, sourceY: 915, sourceDiameter: 82, color: "#ab68e6" },
      { name: "Claude-Opus-4.8", detail: "IKP accuracy 53.9% · 572B", sourceX: 1710, sourceY: 898, sourceDiameter: 74, color: "#ee822f" },
      { name: "Qwen3.7-Max", detail: "IKP accuracy 54.7% · 685B", sourceX: 1792, sourceY: 873, sourceDiameter: 80, color: "#ab68e6" },
      { name: "GLM-5", detail: "IKP accuracy 56.8% · 744B", sourceX: 1832, sourceY: 813, sourceDiameter: 82, color: "#9da3aa" },
      { name: "GLM-5.1", detail: "IKP accuracy 57.8%", sourceX: 1832, sourceY: 785, sourceDiameter: 82, color: "#9da3aa" },
      { name: "Claude-Opus-4.8-Thinking", detail: "IKP accuracy 57.0%", sourceX: 1938, sourceY: 808, sourceDiameter: 92, color: "#ee822f" },
      { name: "Kimi-K2.6", detail: "IKP accuracy 62.4% · 1.0T", sourceX: 1988, sourceY: 655, sourceDiameter: 86, color: "#69aeff" },
      { name: "DeepSeek-V4-Pro (Max)", detail: "IKP accuracy 61.3% · 1.6T", sourceX: 2187, sourceY: 685, sourceDiameter: 92, color: "#4f6aef" },
      { name: "GPT-5.4 (xhigh)", detail: "IKP accuracy 62.1% · 2.2T", sourceX: 2336, sourceY: 661, sourceDiameter: 104, color: "#0ca982" },
      { name: "Gemini-3.5-Flash-Thinking", detail: "IKP accuracy 69.5% · 6.6T", sourceX: 2848, sourceY: 450, sourceDiameter: 122, color: "#fabc05" },
      { name: "GPT-5.5 (xhigh)", detail: "IKP accuracy 71.6% · 9.7T", sourceX: 3028, sourceY: 391, sourceDiameter: 124, color: "#0ca982" },
    ];

    createChartInteraction(document.querySelector("#ikp-chart"), {
      sourceWidth: 4160,
      sourceHeight: 2000,
      points,
    });
  };

  const enhanceFigureLightbox = () => {
    const dialog = document.querySelector("#figure-lightbox");
    const dialogImage = dialog ? dialog.querySelector("img") : null;
    const scroll = dialog ? dialog.querySelector(".lightbox-scroll") : null;
    const closeButton = dialog ? dialog.querySelector(".lightbox-close") : null;
    const triggers = toArray(document.querySelectorAll(".zoomable-figure[data-figure]"));
    let lastTrigger = null;
    if (!dialog || !dialogImage || !scroll || !closeButton) return;

    const clearImage = () => {
      dialogImage.removeAttribute("src");
      dialogImage.alt = "Expanded research figure";
    };

    const close = () => {
      if (dialog.open && typeof dialog.close === "function") dialog.close();
      else {
        dialog.removeAttribute("open");
        clearImage();
        if (lastTrigger) lastTrigger.focus();
      }
    };

    triggers.forEach((trigger) => {
      trigger.addEventListener("click", () => {
        const sourceImage = trigger.querySelector("img");
        lastTrigger = trigger;
        dialogImage.src = trigger.getAttribute("data-figure");
        dialogImage.alt = sourceImage
          ? sourceImage.alt
          : trigger.getAttribute("aria-label") || "Expanded figure";
        scroll.classList.add("is-fit");
        if (typeof dialog.showModal === "function") dialog.showModal();
        else dialog.setAttribute("open", "");
        closeButton.focus();
      });
    });

    closeButton.addEventListener("click", close);
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) close();
    });
    scroll.addEventListener("click", () => scroll.classList.toggle("is-fit"));
    dialog.addEventListener("close", () => {
      clearImage();
      if (lastTrigger) lastTrigger.focus();
    });
  };

  const enhanceNavigation = () => {
    const links = toArray(document.querySelectorAll(".nav-links a[href^='#']"));
    const sections = links
      .map((link) => document.querySelector(link.getAttribute("href")))
      .filter(Boolean);
    if (!links.length || !sections.length || !("IntersectionObserver" in window)) return;

    const setActive = (id) => {
      links.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === `#${id}`);
      });
    };

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible.length) setActive(visible[0].target.id);
      },
      { rootMargin: "-20% 0px -62% 0px", threshold: [0, 0.1, 0.25] }
    );

    sections.forEach((section) => observer.observe(section));
  };

  const enhanceReveal = () => {
    const elements = toArray(document.querySelectorAll(".reveal"));
    if (!elements.length) return;
    if (!("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.08 }
    );

    elements.forEach((element) => observer.observe(element));
  };

  const enhanceBackToTop = () => {
    const button = document.querySelector("#back-to-top");
    if (!button) return;

    const update = () => button.classList.toggle("is-visible", window.scrollY > 700);
    window.addEventListener("scroll", update, { passive: true });
    button.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    update();
  };

  enhancePerformanceChart();
  renderBenchmarkExplorer();
  enhanceTabGroups();
  enhanceIkpChart();
  enhanceFigureLightbox();
  enhanceNavigation();
  enhanceReveal();
  enhanceBackToTop();
})();
