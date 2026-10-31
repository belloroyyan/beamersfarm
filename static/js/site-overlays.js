/*
 * Site overlays: the "how to order" guide plus a few small modal helpers.
 *
 * How the guide works
 * -------------------
 * The browser forgets everything between page loads, so the guide keeps its
 * progress in localStorage under one key. Every page load does the same thing:
 *   1. read the saved state,
 *   2. work out which step the current URL belongs to,
 *   3. draw the right card.
 * Nothing is "dismissed" by pressing Got it. That button only shrinks the card
 * to a small pill. The guide ends when the order is placed (the order-success
 * page is reached) or when the shopper chooses "End the guide".
 */
document.addEventListener("DOMContentLoaded", () => {
  initOrderGuide();
  initModalHelpers();
});

function initOrderGuide() {
  const root = document.querySelector("[data-site-tour]");
  if (!root) return;

  const STORAGE_KEY = "beamers.siteTour.v4";
  const pill = document.querySelector("[data-tour-pill]");
  const el = (name) => root.querySelector(`[data-tour-${name}]`);
  const title = el("title"), copy = el("copy"), eyebrow = el("eyebrow");
  const primary = el("primary"), ack = el("ack"), skip = el("skip");
  const stop = el("stop"), progress = el("progress"), collapse = el("collapse");

  // ---- saved state -------------------------------------------------------
  // started:   the shopper chose "Show me how to order"
  // minimized: the guide is shrunk to the pill
  // finished:  the order was placed and acknowledged, or the guide was ended
  // introDismissed: the shopper picked "Maybe later" on the first card
  let state = {};
  try { state = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); } catch (_) { state = {}; }
  function save(patch) {
    state = { ...state, ...patch };
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (_) { /* private mode: guide still works for this page */ }
  }

  // ---- where is the shopper right now? -----------------------------------
  const path = location.pathname;
  const cartCount = parseFloat((document.querySelector(".cart-count")?.textContent || "0").replace(/[^0-9.]/g, "")) || 0;
  const onOrderSuccess = /^\/order\/[^/]+\/[^/]+\/success\/?$/.test(path);
  const stepIndex = onOrderSuccess ? 3 : path.startsWith("/checkout") ? 2 : path === "/cart" ? 1 : 0;

  // Reaching the success page is the proof that an order was placed.
  if (onOrderSuccess && state.started && !state.finished) save({ placed: true });

  // What each step says. `link` is where the main button goes (null = nothing to click).
  function stepContent() {
    if (stepIndex === 3) {
      return { title: "Order placed. Thank you!", copy: "Keep your order reference and use Track order whenever you want an update.", link: null, label: "Finish" };
    }
    if (stepIndex === 2) {
      return { title: "Choose delivery and payment", copy: "Pick delivery or free farm pickup, check any coupon suggestion, then place the order. The guide ends when your order goes through.", link: null };
    }
    if (stepIndex === 1) {
      return cartCount > 0
        ? { title: "Review your cart", copy: "Check quantities and tick any processing options, press Update cart to save them, then continue.", link: "/checkout", label: "Choose delivery" }
        : { title: "Your cart is empty", copy: "Add a product or package first, then come back here.", link: "/products", label: "Browse products" };
    }
    return cartCount > 0
      ? { title: "Nice, your cart has items", copy: "Keep browsing if you like, or head to your cart to review them.", link: "/cart", label: "Review my cart" }
      : { title: "Pick your products", copy: "Open a product, set the quantity, tick any processing you want, then add it to your cart.", link: path.startsWith("/products") ? null : "/products", label: "Browse products" };
  }

  // ---- drawing -----------------------------------------------------------
  function show(node, visible) { node.hidden = !visible; }

  function draw() {
    const guideActive = Boolean(state.started) && !state.finished;

    if (guideActive) {
      const content = stepContent();
      root.classList.add("is-guide");
      root.removeAttribute("aria-modal");
      eyebrow.textContent = `Step ${stepIndex + 1} of 4`;
      title.textContent = content.title;
      copy.textContent = content.copy;
      show(progress, true);
      progress.querySelectorAll("[data-tour-step]").forEach((item) => {
        const n = Number(item.dataset.tourStep);
        item.classList.toggle("is-done", n < stepIndex || (stepIndex === 3 && state.placed));
        item.classList.toggle("is-current", n === stepIndex);
      });

      if (stepIndex === 3) {
        // Final card: the single button closes the guide for good.
        show(primary, false);
        show(ack, true); ack.textContent = "Finish";
      } else {
        show(primary, Boolean(content.link));
        if (content.link) { primary.href = content.link; primary.textContent = content.label + " →"; }
        show(ack, true); ack.textContent = "Got it";
      }
      show(skip, false);
      show(stop, stepIndex !== 3);
      show(collapse, stepIndex !== 3);

      const minimized = Boolean(state.minimized) && stepIndex !== 3;
      show(root, !minimized);
      show(pill, minimized);
      pill.querySelector("[data-tour-pill-text]").textContent = `Order guide · Step ${stepIndex + 1} of 4`;
      return;
    }

    // Introduction card (not started yet, or restarted from the header icon)
    root.classList.remove("is-guide");
    root.setAttribute("aria-modal", "true");
    eyebrow.textContent = "A quick Beamers guide";
    title.textContent = "Need a tour of the site?";
    copy.textContent = "We can guide you from choosing products to a successful order. The guide stays with you until your order is placed.";
    primary.href = "/products"; primary.textContent = "Show me how to order";
    show(progress, false); show(primary, true); show(ack, false);
    show(skip, true); show(stop, false); show(collapse, true);
    show(pill, false);
    show(root, !state.introDismissed);
  }

  // ---- buttons -----------------------------------------------------------
  primary.addEventListener("click", () => {
    // Starting from the intro card also marks the guide as running.
    if (!state.started || state.finished) save({ started: true, finished: false, placed: false, minimized: false, introDismissed: false });
    // The link itself then navigates to the next page.
  });
  ack.addEventListener("click", () => {
    if (stepIndex === 3) save({ finished: true });      // Finish after an order
    else save({ minimized: true });                      // Got it: shrink, never vanish
    draw();
  });
  skip.addEventListener("click", () => { save({ introDismissed: true }); draw(); });
  collapse.addEventListener("click", () => {
    if (state.started && !state.finished) save({ minimized: true });
    else save({ introDismissed: true });
    draw();
  });
  stop.addEventListener("click", () => { save({ finished: true, started: false }); draw(); });
  pill.addEventListener("click", () => { save({ minimized: false }); draw(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !root.hidden) collapse.click(); });

  // Header icon: reopen the current step, or restart the guide from the beginning.
  document.querySelectorAll("[data-tour-open]").forEach((button) => button.addEventListener("click", () => {
    if (state.started && !state.finished) save({ minimized: false });
    else save({ started: false, finished: false, placed: false, minimized: false, introDismissed: false });
    draw();
    primary.focus?.();
  }));

  draw();
}

function initModalHelpers() {
  document.querySelectorAll("[data-open-customer-modal]").forEach((button) => button.addEventListener("click", () => document.getElementById(button.dataset.openCustomerModal)?.showModal()));
  document.querySelectorAll("[data-close-customer-modal]").forEach((button) => button.addEventListener("click", () => button.closest("dialog")?.close()));
  document.querySelectorAll(".customer-modal").forEach((dialog) => dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); }));
  document.addEventListener("input", (e) => {
    if (!e.target.matches("[data-actions-search]")) return;
    const q = e.target.value.toLowerCase();
    document.querySelectorAll(".owner-actions-panel a").forEach((a) => { a.hidden = q && !a.textContent.toLowerCase().includes(q); });
  });
  document.addEventListener("click", (e) => {
    if (e.target.matches("[data-previous-purchase-close]")) e.target.closest("[data-previous-purchase-panel]")?.remove();
  });
}
