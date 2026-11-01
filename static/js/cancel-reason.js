(() => {
  const init = () => document.querySelectorAll("[data-cancel-reason]").forEach((field) => {
    const select = field.closest("form")?.querySelector('select[name="status"]');
    if (!select) return;
    const sync = () => { field.hidden = select.value !== "Cancelled"; };
    select.addEventListener("change", sync); sync();
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
