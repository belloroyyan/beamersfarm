(() => {
  const init = () => {
    document.querySelectorAll('[data-product-slideshow]').forEach((root) => {
      const slides = [...root.querySelectorAll('.product-slide')];
      if (!slides.length) return;
      root.dataset.slideshowReady = 'true';

      let index = Math.max(0, slides.findIndex((slide) => slide.classList.contains('is-active')));
      if (index < 0) index = 0;

      const count = root.querySelector('[data-slide-count]');
      let dotsContainer = root.querySelector('.product-slideshow-dots');

      // Inject dots if more than one slide and not already present
      if (slides.length > 1 && !dotsContainer) {
        dotsContainer = document.createElement('div');
        dotsContainer.className = 'product-slideshow-dots';
        dotsContainer.setAttribute('role', 'tablist');
        dotsContainer.setAttribute('aria-label', 'Product images');
        slides.forEach((_, i) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.setAttribute('role', 'tab');
          btn.setAttribute('aria-label', `Image ${i + 1}`);
          btn.dataset.slideIndex = i;
          if (i === index) btn.classList.add('is-active');
          btn.addEventListener('click', (e) => {
            e.preventDefault();
            setSlide(i);
          });
          dotsContainer.appendChild(btn);
        });
        root.appendChild(dotsContainer);
      }

      const setSlide = (next) => {
        index = (next + slides.length) % slides.length;
        slides.forEach((slide, position) => {
          const active = position === index;
          slide.classList.toggle('is-active', active);
          slide.setAttribute('aria-hidden', active ? 'false' : 'true');
        });
        if (count) count.textContent = `${index + 1} / ${slides.length}`;
        if (dotsContainer) {
          [...dotsContainer.children].forEach((dot, i) => {
            dot.classList.toggle('is-active', i === index);
            dot.setAttribute('aria-selected', i === index ? 'true' : 'false');
          });
        }
      };

      const move = (amount) => setSlide(index + amount);
      setSlide(index);

      if (slides.length < 2) return;

      root.querySelector('[data-slide-prev]')?.addEventListener('click', (event) => {
        event.preventDefault();
        move(-1);
      });
      root.querySelector('[data-slide-next]')?.addEventListener('click', (event) => {
        event.preventDefault();
        move(1);
      });

      root.tabIndex = 0;
      root.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowLeft') { event.preventDefault(); move(-1); }
        if (event.key === 'ArrowRight') { event.preventDefault(); move(1); }
      });

      let timer = null;
      const stop = () => { if (timer) { window.clearInterval(timer); timer = null; } };
      const start = () => {
        stop();
        if (!document.hidden) {
          timer = window.setInterval(() => move(1), Math.max(2500, Number(root.dataset.interval) || 5000));
        }
      };

      root.addEventListener('mouseenter', stop);
      root.addEventListener('mouseleave', start);
      root.addEventListener('focusin', stop);
      root.addEventListener('focusout', (event) => {
        if (!root.contains(event.relatedTarget)) start();
      });

      let touchStartX = null;
      root.addEventListener('touchstart', (event) => {
        touchStartX = event.changedTouches[0]?.clientX ?? null;
        stop();
      }, { passive: true });
      root.addEventListener('touchend', (event) => {
        if (touchStartX === null) return;
        const delta = event.changedTouches[0].clientX - touchStartX;
        if (Math.abs(delta) > 35) move(delta < 0 ? 1 : -1);
        touchStartX = null;
        start();
      }, { passive: true });

      document.addEventListener('visibilitychange', () => document.hidden ? stop() : start());
      start();
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
