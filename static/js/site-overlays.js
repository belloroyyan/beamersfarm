document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-coupon-gift-popup]").forEach((panel) => {
    const key = `bf_coupon_gift_seen_${panel.dataset.couponId || "latest"}`;
    let seen = false;
    try { seen = localStorage.getItem(key) === "1"; } catch (_) {}
    if (seen) { panel.remove(); return; }
    const dismiss = () => {
      if (!panel.isConnected) return;
      try { localStorage.setItem(key, "1"); } catch (_) {}
      panel.classList.add("is-dismissed");
      window.setTimeout(() => panel.remove(), 220);
    };
    panel.querySelector("[data-coupon-gift-close]")?.addEventListener("click", dismiss);
    panel.querySelector("a")?.addEventListener("click", () => { try { localStorage.setItem(key, "1"); } catch (_) {} });
    window.setTimeout(dismiss, 15000);
  });

  document.querySelectorAll("[data-partner-link-modal]").forEach((modal) => {
    const close = () => modal.remove();
    modal.querySelector("[data-partner-link-close]")?.addEventListener("click", close);
    modal.addEventListener("click", (event) => { if (event.target === modal) close(); });
    modal.querySelector("[data-copy-partner-link]")?.addEventListener("click", async () => {
      const input = modal.querySelector("[data-partner-form-link]");
      const status = modal.querySelector("[data-partner-link-copy-status]");
      try {
        if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(input.value);
        else { input.focus(); input.select(); if (!document.execCommand("copy")) throw new Error("copy failed"); }
        status.textContent = "Link copied. You can now send it to the supplier.";
      } catch (_) { input.focus(); input.select(); status.textContent = "Select the link above and copy it manually."; }
    });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); }, { once: true });
  });

  document.querySelectorAll(".product-photo img").forEach((image) => {
    const markLoaded = () => image.closest(".product-photo")?.classList.add("is-image-loaded");
    if (image.complete && image.naturalWidth > 0) markLoaded();
    else {
      image.addEventListener("load", markLoaded, { once: true });
      image.addEventListener("error", markLoaded, { once: true });
    }
  });
});
