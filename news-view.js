(function () {
  "use strict";

  const grid = document.querySelector(".news-grid");
  const buttons = document.querySelectorAll("[data-news-view]");
  if (!grid || !buttons.length) return;

  const storageKey = "silvermedical-news-view";
  const applyView = (value) => {
    const view = value === "list" ? "list" : "grid";
    grid.classList.toggle("is-list-view", view === "list");
    grid.dataset.view = view;
    buttons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.newsView === view));
    });
  };

  let savedView = "grid";
  try {
    savedView = window.localStorage.getItem(storageKey) || "grid";
  } catch {
    savedView = "grid";
  }
  applyView(savedView);

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const view = button.dataset.newsView;
      applyView(view);
      try {
        window.localStorage.setItem(storageKey, view);
      } catch {
        // The visual switch remains available even when storage is blocked.
      }
    });
  });
})();
