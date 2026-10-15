document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("[data-checkout-form]");
  if (!form) return;
  const panels = [...form.querySelectorAll("[data-checkout-step-panel]")];
  const progress = [...document.querySelectorAll("[data-checkout-progress]")];
  if (panels.length < 3) return;
  let current = 1;

  const setStep = (step) => {
    current = Math.max(1, Math.min(3, step));
    form.classList.add("checkout-wizard-enhanced");
    panels.forEach((panel) => {
      const active = Number(panel.dataset.checkoutStepPanel) === current;
      panel.classList.toggle("is-active", active);
      panel.setAttribute("aria-hidden", active ? "false" : "true");
      if (active) {
        panel.classList.remove("is-entering");
        requestAnimationFrame(() => panel.classList.add("is-entering"));
      }
    });
    progress.forEach((item) => {
      const number = Number(item.dataset.checkoutProgress);
      item.classList.toggle("is-current", number === current);
      item.classList.toggle("is-complete", number < current);
      if (number === current) item.setAttribute("aria-current", "step");
      else item.removeAttribute("aria-current");
    });
    const focusable = panels.find((panel) => Number(panel.dataset.checkoutStepPanel) === current)?.querySelector("input:not([type=hidden]):not([disabled]),select:not([disabled]),textarea:not([disabled]),button");
    if (current > 1) focusable?.focus({ preventScroll: true });
  };

  const validatePanel = (panel) => {
    const candidates = [...panel.querySelectorAll("input, select, textarea")].filter((field) => !field.disabled && field.type !== "hidden");
    for (const field of candidates) {
      if (field.type === "radio") {
        const group = candidates.filter((other) => other.type === "radio" && other.name === field.name);
        if (field.required && !group.some((radio) => radio.checked)) {
          field.focus();
          field.reportValidity?.();
          return false;
        }
        continue;
      }
      if (!field.checkValidity()) {
        field.focus();
        field.reportValidity?.();
        return false;
      }
    }
    return true;
  };

  form.querySelectorAll("[data-checkout-next]").forEach((button) => button.addEventListener("click", () => {
    const panel = panels.find((item) => Number(item.dataset.checkoutStepPanel) === current);
    if (panel && validatePanel(panel)) setStep(current + 1);
  }));
  form.querySelectorAll("[data-checkout-back]").forEach((button) => button.addEventListener("click", () => setStep(current - 1)));
  setStep(1);
});
