/* Shared, delegated dialog controller for all admin create/edit dialogs. */
(() => {
  const findDialog = (id) => {
    if (!id) return null;
    return document.querySelector(`[data-admin-dialog="${CSS.escape(id)}"]`) || document.getElementById(id);
  };

  function placeCreateActions() {
    document.querySelectorAll('.admin-shell > .container, .admin-shell .container').forEach((container) => {
      const action = container.querySelector(':scope > .owner-new-button');
      const heading = container.querySelector(':scope > .admin-topbar');
      if (action && heading && heading.nextElementSibling !== action) {
        heading.insertAdjacentElement('afterend', action);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', placeCreateActions);

  document.addEventListener('click', (event) => {
    const opener = event.target.closest('[data-open-admin-dialog]');
    if (opener) {
      event.preventDefault();
      const dialog = findDialog(opener.dataset.openAdminDialog);
      if (!dialog) {
        console.error('Admin dialog not found:', opener.dataset.openAdminDialog);
        opener.setAttribute('aria-invalid', 'true');
        return;
      }
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
      return;
    }

    const closer = event.target.closest('[data-admin-dialog-close]');
    if (closer) {
      const dialog = closer.closest('dialog');
      if (dialog?.open) dialog.close();
      else dialog?.removeAttribute('open');
      return;
    }

    const editOpener = event.target.closest('[data-open-order-edit]');
    if (editOpener) {
      const dialog = document.getElementById(editOpener.dataset.openOrderEdit);
      if (dialog?.showModal) dialog.showModal();
    }
    const genericCloser = event.target.closest('[data-close-dialog]');
    if (genericCloser) genericCloser.closest('dialog')?.close();
  });

  document.addEventListener('click', (event) => {
    const dialog = event.target;
    if (dialog instanceof HTMLDialogElement && dialog.matches('dialog.admin-panel') && event.target === dialog) {
      dialog.close();
    }
  });
})();
