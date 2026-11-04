/* Expected attributes: dialog[data-admin-dialog="id"], [data-open-admin-dialog="id"], and [data-admin-dialog-close]. */
(() => {
  "use strict";

  const STORAGE_KEY = "active-admin-dialog";
  const dialogSelector = 'dialog[data-admin-dialog]';

  function getDialog(key) {
    if (!key) return null;

    return Array.from(document.querySelectorAll(dialogSelector)).find(
      (dialog) => dialog.getAttribute("data-admin-dialog") === key,
    ) || null;
  }

  function saveDialogKey(key) {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, key);
    } catch (_error) {
      // Storage may be unavailable; dialog behavior should still work.
    }
  }

  function readDialogKey() {
    try {
      return window.sessionStorage.getItem(STORAGE_KEY);
    } catch (_error) {
      return null;
    }
  }

  function clearDialogKey() {
    try {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } catch (_error) {
      // Storage may be unavailable; dialog behavior should still work.
    }
  }

  function openDialog(dialog) {
    const key = dialog.getAttribute("data-admin-dialog");
    if (!key) return;

    saveDialogKey(key);
    if (dialog.open) return;

    try {
      dialog.showModal();
    } catch (_error) {
      // Ignore invalid/unavailable dialog state rather than breaking the page.
    }
  }

  function closeDialog(dialog) {
    if (dialog && dialog.open) dialog.close();
    clearDialogKey();
  }

  function initialize() {
    const dialogs = Array.from(document.querySelectorAll(dialogSelector));

    dialogs.forEach((dialog) => {
      dialog.addEventListener("close", clearDialogKey);
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) closeDialog(dialog);
      });
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!target || typeof target.closest !== "function") return;

      const openButton = target.closest("[data-open-admin-dialog]");
      if (openButton) {
        event.preventDefault();
        const dialog = getDialog(openButton.getAttribute("data-open-admin-dialog"));
        if (dialog) openDialog(dialog);
        return;
      }

      const closeButton = target.closest("[data-admin-dialog-close]");
      if (closeButton) {
        const dialog = closeButton.closest(dialogSelector);
        if (dialog) closeDialog(dialog);
      }
    });

    const hadValidationError = document.querySelector(
      ".flash.error, [data-flash-category=\"error\"]",
    );
    if (!hadValidationError) {
      clearDialogKey();
      return;
    }

    const savedKey = readDialogKey();
    if (!savedKey) return;

    const dialog = getDialog(savedKey);
    if (dialog) {
      openDialog(dialog);
    } else {
      clearDialogKey();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
