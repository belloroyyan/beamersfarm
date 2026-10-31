/* "Clear selected data": live summary of ticked categories, group select-all, and a guarded submit button. */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("[data-clear-form]");
  const list = document.querySelector("#selected-clear-categories");
  if (!form || !list) return;
  const submit = form.querySelector("[data-clear-submit]");
  const confirm = form.querySelector('input[name="confirm"]');
  const fields = () => [...form.querySelectorAll("[data-clear-field]")];
  const labelOf = (field) => field.closest("label")?.querySelector("[data-clear-label]")?.textContent.trim() || field.name;
  const esc = (t) => t.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const render = () => {
    const picked = fields().filter((f) => f.checked);
    list.innerHTML = picked.length
      ? picked.map((f) => `<span class="clear-chip">${esc(labelOf(f))} <button type="button" data-remove="${f.name}" aria-label="Remove ${esc(labelOf(f))}">×</button></span>`).join("")
      : '<span class="field-help">No categories selected yet.</span>';
    form.querySelectorAll(".clear-group").forEach((group) => {
      const boxes = [...group.querySelectorAll("[data-clear-field]")];
      const toggle = group.querySelector("[data-clear-group-toggle]");
      if (toggle) toggle.textContent = boxes.every((b) => b.checked) ? "Clear selection" : "Select all";
    });
    const pins = form.querySelector('[name="reset_pins"]')?.checked;
    const typed = (confirm?.value || "").trim().toUpperCase() === "CLEAR";
    if (submit) submit.disabled = !((picked.length || pins) && typed);
  };

  form.addEventListener("change", render);
  confirm?.addEventListener("input", render);
  list.addEventListener("click", (e) => {
    const name = e.target.closest("[data-remove]")?.dataset.remove;
    if (!name) return;
    const field = form.querySelector(`[name="${name}"]`);
    if (field) field.checked = false;
    render();
  });
  form.querySelectorAll("[data-clear-group-toggle]").forEach((button) => button.addEventListener("click", () => {
    const boxes = [...button.closest(".clear-group").querySelectorAll("[data-clear-field]")];
    const all = boxes.every((b) => b.checked);
    boxes.forEach((b) => { b.checked = !all; });
    render();
  }));
  form.addEventListener("submit", (e) => {
    const picked = fields().filter((f) => f.checked).map(labelOf);
    const summary = picked.length ? picked.join(", ") : "homepage pins";
    if (!window.confirm(`Permanently clear: ${summary}?\n\nThis cannot be undone.`)) e.preventDefault();
  });
  render();
});
