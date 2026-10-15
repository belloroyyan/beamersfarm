document.addEventListener("DOMContentLoaded", () => {
  const dialog = document.querySelector("[data-community-post-dialog]");
  if (!dialog) return;
  const openers = [...document.querySelectorAll("[data-open-community-post]")];
  let lastOpener = null;
  const closeButtons = dialog.querySelectorAll("[data-close-community-post]");
  const textarea = dialog.querySelector("textarea");
  const open = (event) => {
    if (event) event.preventDefault();
    if (event?.currentTarget) lastOpener = event.currentTarget;
    if (dialog.open) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    requestAnimationFrame(() => textarea?.focus({ preventScroll: true }));
  };
  const close = (event) => {
    event?.preventDefault();
    event?.stopPropagation();
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  };
  openers.forEach((button) => button.addEventListener("click", open));
  closeButtons.forEach((button) => button.addEventListener("click", close));
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) close(event);
  });
  dialog.addEventListener("close", () => {
    if (lastOpener?.isConnected) lastOpener.focus({ preventScroll: true });
  });
});
