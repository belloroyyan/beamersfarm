document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-print]").forEach((button) => {
    button.addEventListener("click", () => {
      const hasCover = document.querySelector(".report-overall-cover, .report-cover");
      const includeCover = !hasCover || window.confirm("Print with the Beamers Farms report cover page? Select Cancel to print the report without the cover page.");
      const hidden = hasCover && !includeCover;
      document.body.classList.toggle("print-with-cover", Boolean(hasCover && includeCover));
      document.body.classList.toggle("hide-report-cover", Boolean(hidden));
      const restore = () => {
        document.body.classList.remove("print-with-cover", "hide-report-cover");
        window.removeEventListener("afterprint", restore);
      };
      window.addEventListener("afterprint", restore);
      window.print();
      window.setTimeout(restore, 1200);
    });
  });
});
