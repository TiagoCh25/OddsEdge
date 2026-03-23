(() => {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const target = link.getAttribute("href");
      if (!target || target === "#") return;
      const element = document.querySelector(target);
      if (!(element instanceof HTMLElement)) return;
      event.preventDefault();
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
})();
