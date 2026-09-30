(() => {
  const panel = document.querySelector("[data-staff-push]");
  if (!panel) return;

  const enableButton = panel.querySelector("[data-push-enable]");
  const disableButton = panel.querySelector("[data-push-disable]");
  const status = panel.querySelector("[data-push-status]");
  if (!enableButton || !status) return;

  const say = (message) => { status.textContent = message; };
  const unsupported = !("serviceWorker" in navigator)
    || !("PushManager" in window)
    || !("Notification" in window);

  if (unsupported) {
    enableButton.disabled = true;
    if (disableButton) disableButton.hidden = true;
    say("Push notifications are not supported by this browser. The staff desk remains available while online.");
    return;
  }

  if (Notification.permission === "denied") {
    enableButton.disabled = true;
    if (disableButton) disableButton.hidden = true;
    say("Notifications are blocked in this browser. Allow them in browser settings, then reload this page.");
    return;
  }

  navigator.serviceWorker.ready
    .then((registration) => registration.pushManager.getSubscription())
    .then((subscription) => {
      if (subscription) {
        enableButton.textContent = "Sync alerts on this device";
        if (disableButton) disableButton.hidden = false;
        say("This browser already has a push subscription. Sync it here, or disable alerts for this device.");
      }
    })
    .catch(() => say("Could not check this device’s notification status. You can still try enabling it."));

  enableButton.addEventListener("click", async () => {
    enableButton.disabled = true;
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        say(permission === "denied"
          ? "Notifications are blocked. Change this in browser settings if you want staff alerts."
          : "Notification permission was not granted. You can enable it later from this page.");
        return;
      }

      const registration = await navigator.serviceWorker.ready;
      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        const encodedKey = panel.dataset.vapidPublicKey;
        const paddedKey = encodedKey + "=".repeat((4 - (encodedKey.length % 4)) % 4);
        const binaryKey = atob(paddedKey.replace(/-/g, "+").replace(/_/g, "/"));
        const applicationServerKey = Uint8Array.from(binaryKey, (character) => character.charCodeAt(0));
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey,
        });
      }

      const response = await fetch(panel.dataset.subscriptionUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": panel.dataset.csrfToken,
        },
        body: JSON.stringify(subscription.toJSON()),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Could not save this device’s subscription.");

      enableButton.textContent = "Sync alerts on this device";
      if (disableButton) disableButton.hidden = false;
      say(result.message || "Notifications are enabled for this device.");
    } catch (error) {
      say(error && error.message ? error.message : "Could not enable notifications on this device.");
    } finally {
      if (Notification.permission !== "denied") enableButton.disabled = false;
    }
  });

  if (disableButton) {
    disableButton.addEventListener("click", async () => {
      disableButton.disabled = true;
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
          disableButton.hidden = true;
          say("There is no active push subscription on this device.");
          return;
        }
        const response = await fetch(panel.dataset.subscriptionUrl, {
          method: "DELETE",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": panel.dataset.csrfToken,
          },
          body: JSON.stringify({ endpoint: subscription.endpoint }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result.error || "Could not disable alerts for this device.");
        await subscription.unsubscribe();
        enableButton.textContent = "Enable alerts on this device";
        disableButton.hidden = true;
        say("Alerts have been disabled for this device.");
      } catch (error) {
        say(error && error.message ? error.message : "Could not disable alerts for this device.");
      } finally {
        disableButton.disabled = false;
      }
    });
  }
})();
