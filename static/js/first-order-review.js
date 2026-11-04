(() => {
  "use strict";

  const dialog = document.querySelector("[data-first-order-review]");
  if (!dialog || typeof dialog.showModal !== "function") return;

  const orderUuid = dialog.getAttribute("data-order-uuid") || "order";
  const storageKey = `beamers-review-dismissed:${orderUuid}`;
  let dismissed = false;
  try {
    dismissed = window.sessionStorage.getItem(storageKey) === "1";
  } catch (_error) {
    // The review prompt remains usable when browser storage is unavailable.
  }

  const markDismissed = () => {
    try {
      window.sessionStorage.setItem(storageKey, "1");
    } catch (_error) {
      // Storage is only used to avoid repeating a prompt after it is dismissed.
    }
  };

  dialog.addEventListener("cancel", markDismissed);
  dialog.addEventListener("close", markDismissed);
  dialog.querySelectorAll("[data-first-review-close]").forEach((button) => {
    button.addEventListener("click", () => dialog.close());
  });

  if (!dismissed) dialog.showModal();
})();
