(() => {
  if (!("serviceWorker" in navigator) || !window.isSecureContext) return;

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js", { scope: "/" })
      .catch((error) => console.warn("Beamers Farm offline support could not be enabled.", error));
  });
})();
