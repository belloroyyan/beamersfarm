/*
 * Keeps every <details> dropdown panel (Actions, Community actions, header "Menu")
 * fully inside the viewport, on any screen width. CSS gives a sensible default;
 * this measures the real position after opening and nudges the panel if needed.
 */
(function () {
  const MARGIN = 12;
  // At or below this width the header "Menu" group is not a dropdown: its links are
  // part of the hamburger list and the <details> must stay open (see cart.js).
  const mobileNav = window.matchMedia("(max-width: 1040px)");
  const isFlatNav = (d) => d.matches(".nav-more") && mobileNav.matches;
  const PANEL = ".owner-actions-panel, .community-action-panel, .nav-more-menu, .sales-actions-panel";

  function fit(details) {
    const panel = details.querySelector(PANEL);
    if (!panel || getComputedStyle(panel).position !== "absolute") return;
    panel.style.removeProperty("--fit-shift");
    panel.style.removeProperty("max-width");
    const vw = document.documentElement.clientWidth;
    panel.style.maxWidth = Math.max(220, vw - MARGIN * 2) + "px";
    const rect = panel.getBoundingClientRect();
    let shift = 0;
    if (rect.left < MARGIN) shift = MARGIN - rect.left;
    else if (rect.right > vw - MARGIN) shift = (vw - MARGIN) - rect.right;
    if (shift) panel.style.setProperty("--fit-shift", Math.round(shift) + "px");
  }

  function closeOthers(current) {
    document.querySelectorAll("details.owner-actions-menu[open], details.community-action-menu[open], details.nav-more[open]").forEach((d) => { if (d !== current) d.removeAttribute("open"); });
  }

  document.addEventListener("toggle", (event) => {
    const d = event.target;
    if (!(d instanceof HTMLDetailsElement) || !d.matches(".owner-actions-menu, .community-action-menu, .nav-more")) return;
    if (isFlatNav(d)) { if (!d.open) d.open = true; return; }
    if (d.open) { closeOthers(d); requestAnimationFrame(() => fit(d)); }
  }, true);

  // Click outside or Escape closes an open dropdown.
  document.addEventListener("click", (event) => {
    document.querySelectorAll("details.owner-actions-menu[open], details.community-action-menu[open], details.nav-more[open]").forEach((d) => { if (isFlatNav(d)) return; if (!d.contains(event.target)) d.removeAttribute("open"); });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    document.querySelectorAll("details.owner-actions-menu[open], details.community-action-menu[open], details.nav-more[open]").forEach((d) => { if (isFlatNav(d)) return; d.removeAttribute("open"); d.querySelector("summary")?.focus(); });
  });

  // Crossing into the mobile breakpoint re-opens the flattened group; leaving it collapses the dropdown.
  const syncFlatNav = () => document.querySelectorAll("details.nav-more").forEach((d) => { d.open = mobileNav.matches; });
  mobileNav.addEventListener?.("change", syncFlatNav);
  syncFlatNav();

  let t;
  window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => document.querySelectorAll("details[open]").forEach(fit), 80); });
  window.addEventListener("orientationchange", () => document.querySelectorAll("details[open]").forEach(fit));

  // Mark the current page in the header so the nav can show where you are.
  const here = window.location.pathname.replace(/\/+$/, "") || "/";
  document.querySelectorAll(".main-nav a[href]").forEach((a) => {
    let path;
    try { path = new URL(a.href, window.location.origin).pathname.replace(/\/+$/, "") || "/"; } catch (_) { return; }
    const match = path === here || (path !== "/" && here.startsWith(path + "/"));
    if (!match) return;
    a.setAttribute("aria-current", "page");
    a.closest(".nav-more")?.classList.add("is-current");
  });
})();
