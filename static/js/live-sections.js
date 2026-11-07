/* Adaptive partial refresh: pauses in hidden tabs, backs off on errors, and avoids overlapping work. */
(() => {
  const selectors = ['[data-live-section]', '.live-stream-list', '.community-feed', '.operational-metrics', '.live-order-table', '.live-notification-list'];
  const BASE_INTERVAL = 30000;
  const MAX_INTERVAL = 120000;
  let timer = null;
  let busy = false;
  let failures = 0;

  function targetsNow() {
    return [...new Set(selectors.flatMap((selector) => [...document.querySelectorAll(selector)]))];
  }

  async function refresh() {
    if (busy || document.visibilityState !== 'visible') return;
    const targets = targetsNow();
    if (!targets.length) return;
    // Do not spend a request while the user is actively editing or filtering a live region.
    if (targets.some((node) => node.contains(document.activeElement))) return;
    busy = true;
    try {
      const response = await fetch(window.location.href, {
        headers: {'X-Requested-With': 'XMLHttpRequest', 'Accept': 'text/html'},
        cache: 'no-store', credentials: 'same-origin'
      });
      if (!response.ok) throw new Error(`Live refresh failed (${response.status})`);
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
      for (const current of targets) {
        const selector = current.matches('[data-live-section]')
          ? `[data-live-section="${CSS.escape(current.dataset.liveSection)}"]`
          : [...current.classList].map((c) => `.${CSS.escape(c)}`).join('');
        const replacement = parsed.querySelector(selector);
        if (!replacement || !current.isConnected || current.contains(document.activeElement)) continue;
        current.replaceWith(replacement.cloneNode(true));
      }
      failures = 0;
      document.dispatchEvent(new CustomEvent('beamers:live-sections-updated'));
    } catch (_) {
      failures = Math.min(failures + 1, 4);
    } finally {
      busy = false;
      schedule();
    }
  }

  function schedule() {
    window.clearTimeout(timer);
    if (document.visibilityState !== 'visible' || !targetsNow().length) return;
    const delay = Math.min(BASE_INTERVAL * (2 ** failures), MAX_INTERVAL);
    timer = window.setTimeout(refresh, delay);
  }

  document.addEventListener('visibilitychange', () => {
    window.clearTimeout(timer);
    if (document.visibilityState === 'visible') refresh();
  });
  window.addEventListener('focus', schedule);
  window.addEventListener('pageshow', schedule);
  schedule();
})();
