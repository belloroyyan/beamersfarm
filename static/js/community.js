document.addEventListener("DOMContentLoaded", () => {
  const dialog = document.querySelector("[data-community-post-dialog]");
  const replyDialog = document.querySelector("[data-community-reply-dialog]");
  if (replyDialog) {
    const form = replyDialog.querySelector("[data-reply-form]");
    const text = replyDialog.querySelector("textarea");
    let lastReplyOpener = null;
    document.querySelectorAll("[data-open-community-reply]").forEach((button) => button.addEventListener("click", (event) => {
      event.preventDefault(); lastReplyOpener = button; form.action = `/community/posts/${button.dataset.postId}/comments`;
      replyDialog.showModal ? replyDialog.showModal() : replyDialog.setAttribute("open", "");
      requestAnimationFrame(() => text?.focus({preventScroll:true}));
    }));
    replyDialog.querySelectorAll("[data-close-community-reply]").forEach((button) => button.addEventListener("click", (event) => { event.preventDefault(); replyDialog.close ? replyDialog.close() : replyDialog.removeAttribute("open"); }));
    replyDialog.addEventListener("click", (event) => { if (event.target === replyDialog) replyDialog.close(); });
    replyDialog.addEventListener("close", () => lastReplyOpener?.focus({preventScroll:true}));
  }
  const special = document.querySelector("[data-special-post-dialog]");
  if (special) {
    document.querySelectorAll("[data-open-special-post]").forEach((b) => b.addEventListener("click", () => {
      special.showModal ? special.showModal() : special.setAttribute("open", "");
      requestAnimationFrame(() => special.querySelector("textarea")?.focus({ preventScroll: true }));
    }));
    special.querySelectorAll("[data-close-special-post]").forEach((b) => b.addEventListener("click", () => special.close ? special.close() : special.removeAttribute("open")));
    special.addEventListener("click", (e) => { if (e.target === special) special.close(); });
  }
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
