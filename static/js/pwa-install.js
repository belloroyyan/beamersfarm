(() => {
  const button = document.querySelector("[data-install-app]");
  if (!button) return;

  let deferredPrompt = null;
  const standalone = () => window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;

  if (standalone()) {
    button.hidden = true;
    return;
  }

  button.textContent = "Install Beamers";

  // Do not cancel this event. Allow supported browsers to show their
  // native install UI; retain the event so the in-page button can also prompt
  // after a user gesture when the browser exposes that flow.
  window.addEventListener("beforeinstallprompt", (event) => {
    deferredPrompt = event;
    button.hidden = false;
  });

  button.addEventListener("click", async () => {
    if (!deferredPrompt) return;

    const promptEvent = deferredPrompt;
    deferredPrompt = null;
    button.disabled = true;

    try {
      await promptEvent.prompt();
      const choice = await promptEvent.userChoice;
      if (choice && choice.outcome === "accepted") button.hidden = true;
    } catch (error) {
      // The browser may consume the event while showing its native banner.
      // Keep the button usable without surfacing an unhandled promise error.
      button.hidden = true;
    } finally {
      button.disabled = false;
    }
  });

  window.addEventListener("appinstalled", () => {
    button.hidden = true;
    deferredPrompt = null;
  });
})();
