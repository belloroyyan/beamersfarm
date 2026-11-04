(() => {
  "use strict";

  const init = () => {
    const reportPage = document.querySelector(".staff-report-page");
    const trigger = document.querySelector("[data-print]");
    const dialog = document.querySelector("[data-staff-print-dialog]");
    const withLogs = document.querySelector("[data-print-with-actions]");
    const withoutLogs = document.querySelector("[data-print-without-actions]");

    if (!reportPage || !trigger || !dialog || !withLogs || !withoutLogs) return;

    const openPrompt = () => {
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      } else {
        const include = window.confirm("Include staff action logs in the printout or saved PDF?");
        printReport(!include);
      }
    };

    const printReport = (omitLogs) => {
      let restored = false;
      let fallbackTimer;
      const restore = () => {
        if (restored) return;
        restored = true;
        window.removeEventListener("afterprint", restore);
        window.clearTimeout(fallbackTimer);
        reportPage.classList.remove("staff-report-hide-actions");
      };
      if (omitLogs) reportPage.classList.add("staff-report-hide-actions");
      window.addEventListener("afterprint", restore);
      fallbackTimer = window.setTimeout(restore, 30000);
      window.print();
    };

    trigger.addEventListener("click", openPrompt);
    withLogs.addEventListener("click", () => {
      dialog.close();
      printReport(false);
    });
    withoutLogs.addEventListener("click", () => {
      dialog.close();
      printReport(true);
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
