/* MetaAutomate static business site.
   No analytics, cookies, tokens, external requests or backend dependencies. */
(() => {
  "use strict";
  const toggle = document.getElementById("menu-toggle");
  const nav = document.getElementById("primary-navigation");
  const header = document.querySelector(".site-header");

  function setMenu(open) {
    nav?.classList.toggle("is-open", open);
    toggle?.setAttribute("aria-expanded", String(open));
    toggle?.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  }

  toggle?.addEventListener("click", () => {
    setMenu(toggle.getAttribute("aria-expanded") !== "true");
  });
  nav?.addEventListener("click", (event) => {
    if (event.target.closest("a")) setMenu(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && toggle?.getAttribute("aria-expanded") === "true") {
      setMenu(false);
      toggle.focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (toggle && nav && !toggle.contains(event.target) && !nav.contains(event.target)) {
      setMenu(false);
    }
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth > 980) setMenu(false);
  });

  function updateHeader() {
    header?.classList.toggle("is-scrolled", window.scrollY > 24);
  }
  updateHeader();
  window.addEventListener("scroll", updateHeader, {passive:true});

  const buttons = [...document.querySelectorAll(".filter-button")];
  const cards = [...document.querySelectorAll(".capability-card")];
  const status = document.createElement("p");
  status.className = "visually-hidden";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  document.querySelector(".filter-group")?.after(status);
  function filterCapabilities(selected) {
    let visibleCount = 0;
    for (const card of cards) {
      const categoryList = (card.dataset.categories || "").split(/\s+/);
      const show = selected === "all" || categoryList.includes(selected);
      card.hidden = !show;
      if (show) visibleCount++;
    }
    for (const button of buttons) {
      const active = button.dataset.filter === selected;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    }
    status.textContent = "Showing " + visibleCount + " of " + cards.length + " capabilities";
  }
  for (const button of buttons) {
    button.addEventListener("click", () => filterCapabilities(button.dataset.filter));
  }
  filterCapabilities("all");

  const year = document.getElementById("copyright-year");
  if (year) year.textContent = String(new Date().getFullYear());
})();