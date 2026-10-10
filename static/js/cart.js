document.addEventListener('DOMContentLoaded', () => {
  const menuButton = document.querySelector('.menu-toggle');
  const menu = document.querySelector('#main-menu');
  const moreMenu = menu && menu.querySelector('.nav-more');
  const ownerActionsMenus = document.querySelectorAll('.owner-actions-menu');
  if (menuButton && menu) {
    const mobileNavQuery = window.matchMedia('(max-width: 700px)');
    const syncMoreMenu = () => {
      // On mobile, More is not a second menu: its links are part of the
      // hamburger list. Keep the native details element open so its children
      // remain visible when the summary is hidden by CSS.
      if (moreMenu) moreMenu.open = mobileNavQuery.matches;
    };
    syncMoreMenu();
    mobileNavQuery.addEventListener?.('change', syncMoreMenu);
    const closeMenu = () => {
      menu.classList.remove('is-open');
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.setAttribute('aria-label', 'Open menu');
    };
    menuButton.addEventListener('click', () => {
      const open = menu.classList.toggle('is-open');
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      syncMoreMenu();
    });
    menu.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));
    document.addEventListener('click', (event) => {
      if (!menu.contains(event.target) && !menuButton.contains(event.target)) closeMenu();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeMenu();
        if (moreMenu && !mobileNavQuery.matches) moreMenu.open = false;
        ownerActionsMenus.forEach((actions) => {
          if (actions.open) {
            actions.open = false;
            actions.querySelector('summary')?.focus();
          }
        });
      }
    });
    document.addEventListener('click', (event) => {
      if (moreMenu && !mobileNavQuery.matches && !moreMenu.contains(event.target)) moreMenu.open = false;
    });
    document.addEventListener('click', (event) => {
      ownerActionsMenus.forEach((actions) => {
        if (actions.open && !actions.contains(event.target)) actions.open = false;
      });
    });
  }

  document.querySelectorAll('.flash').forEach((flash) => {
    window.setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transition = 'opacity .35s ease';
      window.setTimeout(() => flash.remove(), 400);
    }, 5000);
  });

  document.querySelectorAll('[data-fractional-quantity-toggle]').forEach((toggle) => {
    const form = toggle.closest('form');
    const stockInput = form && form.querySelector('[data-stock-quantity]');
    if (!stockInput) return;
    const syncStep = () => { stockInput.step = toggle.checked ? '0.001' : '1'; };
    syncStep();
    toggle.addEventListener('change', syncStep);
  });

  document.querySelectorAll('input[type="number"]').forEach((input) => {
    input.addEventListener('change', () => {
      const min = Number(input.min || 0);
      const max = Number(input.max || Number.MAX_SAFE_INTEGER);
      const value = Number(input.value || 0);
      input.value = Math.min(Math.max(value, min), max);
    });
  });
});
