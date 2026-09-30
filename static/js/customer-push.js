(() => {
  const panel = document.querySelector("[data-customer-push]");
  if (!panel) return;

  const button = panel.querySelector("[data-customer-push-enable]");
  const status = panel.querySelector("[data-customer-push-status]");
  if (!button || !status) return;

  const say = (message) => { status.textContent = message; };
  const apiUrl = panel.dataset.subscriptionUrl;
  const csrfToken = panel.dataset.csrfToken;
  const showEnableButton = () => { button.hidden = false; };
  const request = async (payload) => {
    const response = await fetch(apiUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Could not update notification settings.");
    return result;
  };

  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
    say("This browser does not support push notifications. Keep your order reference to check back with us.");
    return;
  }

  if (Notification.permission === "denied") {
    say("Notifications are blocked for this site. You can allow them in your browser settings if you change your mind.");
    return;
  }

  say("Checking whether this device already has order notifications enabled…");
  navigator.serviceWorker.ready
    .then(async (registration) => {
      const subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        say("Enable a notification for this device to hear when your order is confirmed.");
        showEnableButton();
        return;
      }

      try {
        const result = await request({ action: "check", endpoint: subscription.endpoint });
        if (result.enabled) {
          say("Order notifications are already enabled on this device. No new prompt is needed.");
        } else {
          say("Enable a notification for this device to hear when your order is confirmed.");
          showEnableButton();
        }
      } catch (_) {
        say("Could not check this device’s order-notification setting. You can still choose to enable it.");
        showEnableButton();
      }
    })
    .catch(() => {
      say("Could not check notification support on this device. You can still try enabling it.");
      showEnableButton();
    });

  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        say(permission === "denied"
          ? "Notifications were not allowed. You can change this in browser settings."
          : "Notification permission was not granted. You can enable it later from this receipt.");
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

      const result = await request({ action: "subscribe", ...subscription.toJSON() });
      say(result.message || "Notifications are enabled for this order.");
      button.hidden = true;
    } catch (error) {
      say(error && error.message ? error.message : "Could not enable order notifications on this device.");
      showEnableButton();
    } finally {
      button.disabled = false;
    }
  });
})();
