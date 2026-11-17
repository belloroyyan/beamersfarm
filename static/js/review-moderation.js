document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".review-moderate-trigger");
    if (trigger) {
      event.preventDefault();
      const id = trigger.dataset.dialog;
      const dialog = id ? document.getElementById(id) : null;
      trigger.closest("details")?.removeAttribute("open");
      if (!dialog) {
        console.error("Review moderation dialog was not found:", id);
        return;
      }
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      return;
    }
    const close = event.target.closest(".review-dialog-close, .review-dialog-cancel");
    if (close) {
      const dialog = close.closest("dialog");
      if (dialog?.close) dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    const dialog = event.target.closest(".review-moderation-dialog");
    if (dialog && event.target === dialog) {
      if (dialog.close) dialog.close();
      else dialog.removeAttribute("open");
    }
    document.querySelectorAll(".review-actions-menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });
});
