(() => {
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const toArray = (collection) => Array.prototype.slice.call(collection || []);
  const empty = (element) => {
    while (element && element.firstChild) element.removeChild(element.firstChild);
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
      button.style.setProperty("--point-color", point.color || "#df2f2f");
      button.style.setProperty("--point-size", `${point.size || 34}px`);
      button.style.width = `${point.size || 34}px`;
      button.style.height = `${point.size || 34}px`;
      button.addEventListener("mouseenter", () => activate(button, point));
      button.addEventListener("focus", () => activate(button, point));
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        activate(button, point);
      });
      buttons.push(button);
      hotspotLayer.appendChild(button);
    });

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

  const formatScore = (score) => {
    const fixed = score.toFixed(2);
    return fixed.replace(/\.00$/, "").replace(/(\.\d)0$/, "$1");
  };

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

    const renderRanking = (dataset) => {
      const models = data.models
        .filter((model) => Number.isFinite(model.scores[dataset.id]))
        .slice()
        .sort((a, b) => b.scores[dataset.id] - a.scores[dataset.id]);
      const ours = models.find((model) => model.isOurs) || models[0];
      const ourRank = models.indexOf(ours) + 1;

      renderSummary(dataset, ours, ourRank, models.length);
      empty(rankingRoot);
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

    const activateTab = (index, moveFocus) => {
      activeIndex = (index + data.datasets.length) % data.datasets.length;
      tabButtons.forEach((button, buttonIndex) => {
        const selected = buttonIndex === activeIndex;
        button.setAttribute("aria-selected", selected ? "true" : "false");
        button.tabIndex = selected ? 0 : -1;
      });
      renderRanking(data.datasets[activeIndex]);
      if (moveFocus) {
        tabButtons[activeIndex].focus();
        if (typeof tabButtons[activeIndex].scrollIntoView === "function") {
          tabButtons[activeIndex].scrollIntoView({ block: "nearest", inline: "nearest" });
        }
      }
    };

    data.datasets.forEach((dataset, index) => {
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
          activateTab(data.datasets.length - 1, true);
        }
      });
      tabButtons.push(button);
      tabsRoot.appendChild(button);
    });

    activateTab(0, false);
  };

  const enhanceEvidenceTabs = () => {
    const buttons = toArray(document.querySelectorAll(".evidence-tabs [role='tab']"));
    const panels = toArray(document.querySelectorAll(".evidence-panel[role='tabpanel']"));
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
  enhanceEvidenceTabs();
  enhanceIkpChart();
  enhanceFigureLightbox();
  enhanceNavigation();
  enhanceReveal();
  enhanceBackToTop();
})();
