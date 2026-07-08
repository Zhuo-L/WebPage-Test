(() => {
  const figures = document.querySelectorAll(".interactive-figure");

  figures.forEach((figure) => {
    const note = figure.querySelector(".figure-note");
    const title = note?.querySelector("strong");
    const body = note?.querySelector("p");
    const hotspots = Array.from(figure.querySelectorAll(".hotspot"));
    const controls = Array.from(figure.querySelectorAll(".figure-control"));

    if (!note || !title || !body || hotspots.length === 0) {
      return;
    }

    const setActive = (hotspot) => {
      const key = hotspot.dataset.key;
      hotspots.forEach((item) => item.classList.toggle("is-active", item === hotspot));
      controls.forEach((item) => item.classList.toggle("is-active", item.dataset.key === key));
      figure.classList.add("has-active");
      title.textContent = hotspot.dataset.title || "";
      body.textContent = hotspot.dataset.body || "";
    };

    const activateByKey = (key) => {
      const target = hotspots.find((item) => item.dataset.key === key);

      if (target) {
        setActive(target);
      }
    };

    hotspots.forEach((hotspot, index) => {
      hotspot.type = "button";
      hotspot.addEventListener("mouseenter", () => setActive(hotspot));
      hotspot.addEventListener("focus", () => setActive(hotspot));
      hotspot.addEventListener("click", (event) => {
        event.preventDefault();
        setActive(hotspot);
      });

      if (index === 0) {
        setActive(hotspot);
      }
    });

    controls.forEach((control) => {
      control.type = "button";
      const activate = () => activateByKey(control.dataset.key);

      control.addEventListener("mouseenter", activate);
      control.addEventListener("focus", activate);
      control.addEventListener("click", (event) => {
        event.preventDefault();
        activate();
      });
    });

    figure.addEventListener("mouseleave", () => {
      const active = figure.querySelector(".hotspot.is-active") || hotspots[0];
      setActive(active);
    });
  });
})();
