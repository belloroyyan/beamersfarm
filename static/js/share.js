/*
 * Share button for receipts and summaries: <button data-share>Share</button>
 *
 * Optional attributes: data-share-title, data-share-text, data-share-url
 * (defaults: page title and current address).
 *
 * 1. Uses the native share sheet where the browser provides one (needs HTTPS
 *    and a tap, which a click handler satisfies).
 * 2. Otherwise copies the link to the clipboard.
 * 3. If the clipboard API is blocked, falls back to a hidden-textarea copy and,
 *    as a last resort, a prompt() so the person can copy the address by hand.
 * The button label announces the result and then resets.
 */
(() => {
  const copyText = async (value) => {
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(value); return true; } catch (_) { /* fall through */ }
    }
    const field = document.createElement("textarea");
    field.value = value;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    field.setSelectionRange(0, value.length);
    let copied = false;
    try { copied = document.execCommand("copy"); } catch (_) { copied = false; }
    field.remove();
    return copied;
  };

  const init = () => {
    document.querySelectorAll("[data-share]").forEach((button) => {
      if (button.dataset.shareBound) return;
      button.dataset.shareBound = "1";
      const original = button.textContent.trim() || "Share";
      let status = button.parentElement && button.parentElement.querySelector("[data-share-status]");
      if (!status) {
        status = document.createElement("span");
        status.className = "sr-only";
        status.setAttribute("role", "status");
        status.setAttribute("aria-live", "polite");
        status.dataset.shareStatus = "";
        button.insertAdjacentElement("afterend", status);
      }
      const say = (label, message) => {
        button.textContent = label;
        status.textContent = message || label;
        window.setTimeout(() => { button.textContent = original; }, 2200);
      };

      button.addEventListener("click", async (event) => {
        event.preventDefault();
        const data = {
          title: button.dataset.shareTitle || document.title,
          text: button.dataset.shareText || document.title,
          url: button.dataset.shareUrl || window.location.href,
        };
        if (navigator.share) {
          try {
            if (navigator.canShare && !navigator.canShare(data)) throw new TypeError("unsupported share data");
            await navigator.share(data);
            return say("Shared", "Shared.");
          } catch (error) {
            if (error && error.name === "AbortError") return; // person closed the share sheet
            // Any other failure: fall through to copying the link.
          }
        }
        if (await copyText(data.url)) return say("Link copied", "Link copied to the clipboard.");
        window.prompt("Copy this link to share it:", data.url);
        say(original, "Copy the link from the box that appeared.");
      });
    });
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
