document.addEventListener('DOMContentLoaded', () => {
  const menuButton = document.querySelector('.menu-toggle');
  const menu = document.querySelector('#main-menu');
  if (menuButton && menu) {
    const closeMenu = () => {
      menu.classList.remove('is-open');
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.setAttribute('aria-label', 'Open menu');
    };
    menuButton.addEventListener('click', () => {
      const open = menu.classList.toggle('is-open');
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
    menu.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));
    document.addEventListener('click', (event) => {
      if (!menu.contains(event.target) && !menuButton.contains(event.target)) closeMenu();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeMenu();
    });
  }

  document.querySelectorAll('.flash').forEach((flash) => {
    window.setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transition = 'opacity .35s ease';
      window.setTimeout(() => flash.remove(), 400);
    }, 5000);
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
