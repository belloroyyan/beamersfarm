(() => {
  const KEY = "beamers.notificationPrompt.lastSeen";
  const DAY = 24 * 60 * 60 * 1000;
  const read = () => { try { return Number(localStorage.getItem(KEY)) || 0; } catch (_) { return 0; } };
  const stamp = () => { try { localStorage.setItem(KEY, String(Date.now())); } catch (_) { /* storage blocked */ } };

  const init = () => {
    const panel = document.querySelector(".site-notification-prompt");
    if (!panel) return;
    const supported = "Notification" in window;
    // Nothing to ask once the browser has already answered, or when it cannot show notifications.
    if (!supported || Notification.permission !== "default") return panel.remove();
    // Shown at most once per day.
    if (Date.now() - read() < DAY) return panel.remove();

    const close = () => { stamp(); panel.remove(); };
    stamp();                                   // counts as today's showing even if never dismissed
    panel.classList.add("is-visible");
    panel.querySelector("[data-site-notifications-dismiss]")?.addEventListener("click", close);
    panel.querySelector("a[href]")?.addEventListener("click", stamp);
    panel.querySelector("[data-site-notifications-enable]")?.addEventListener("click", async () => {
      const result = await Notification.requestPermission();
      if (result !== "default") close();
    });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
