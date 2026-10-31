/* Secure drop: the "New drop" form lives in a modal dialog, like the community "New post" popup. */
document.addEventListener("DOMContentLoaded", () => {
  const dialog = document.querySelector("[data-drop-dialog]");
  const created = document.querySelector("[data-drop-created]");
  const open = (d) => { if (!d || d.open) return; (typeof d.showModal === "function") ? d.showModal() : d.setAttribute("open", ""); };
  const close = (d) => { if (!d) return; (typeof d.close === "function" && d.open) ? d.close() : d.removeAttribute("open"); };

  let lastOpener = null;
  document.querySelectorAll("[data-open-drop-dialog]").forEach((button) => button.addEventListener("click", (event) => {
    event.preventDefault(); lastOpener = button; open(dialog);
    requestAnimationFrame(() => dialog?.querySelector("textarea, select")?.focus({ preventScroll: true }));
  }));
  document.querySelectorAll("dialog.drop-dialog").forEach((d) => {
    d.querySelectorAll("[data-close-drop-dialog]").forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); close(d); }));
    d.addEventListener("click", (e) => { if (e.target === d) close(d); });
    d.addEventListener("close", () => { if (lastOpener?.isConnected) lastOpener.focus({ preventScroll: true }); });
  });

  // Text vs file switch
  const kind = dialog?.querySelector("[data-drop-kind]");
  const text = dialog?.querySelector("[data-drop-text]");
  const file = dialog?.querySelector("[data-drop-file]");
  const sync = () => {
    const isText = !kind || kind.value === "text";
    if (text) text.hidden = !isText;
    if (file) file.hidden = isText;
  };
  kind?.addEventListener("change", sync); sync();

  // A new one-time link opens automatically after saving.
  if (created) open(created);

  document.querySelectorAll("[data-copy-drop-link]").forEach((button) => button.addEventListener("click", async () => {
    const input = document.querySelector("[data-drop-link]");
    try { await navigator.clipboard.writeText(input.value); }
    catch (_) { input.select(); document.execCommand("copy"); }
    button.textContent = "Copied";
  }));
});

/* Copy buttons (vault rows and the one-time text page). */
(() => {
  const copy = async (value) => {
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(value); return true; } catch (_) { /* fall back */ }
    }
    const field = document.createElement("textarea");
    field.value = value; field.setAttribute("readonly", "");
    field.style.position = "fixed"; field.style.opacity = "0";
    document.body.appendChild(field); field.select();
    let ok = false; try { ok = document.execCommand("copy"); } catch (_) { ok = false; }
    field.remove(); return ok;
  };
  const flash = (button, label) => {
    const original = button.dataset.label || (button.dataset.label = button.textContent.trim());
    button.textContent = label;
    window.setTimeout(() => { button.textContent = original; }, 1800);
  };
  const init = () => {
    document.querySelectorAll("[data-copy-text]").forEach((button) => button.addEventListener("click", async () => {
      flash(button, (await copy(button.dataset.copyText)) ? "Copied" : "Copy failed");
    }));
    document.querySelectorAll("[data-copy-drop-text]").forEach((button) => button.addEventListener("click", async () => {
      const source = document.querySelector("[data-drop-text-content]");
      const status = document.querySelector("[data-drop-action-status]");
      const ok = source ? await copy(source.textContent) : false;
      flash(button, ok ? "Copied" : "Copy failed");
      if (status) status.textContent = ok ? "Text copied to the clipboard." : "Copy was blocked. Select the text and copy it manually.";
    }));
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
