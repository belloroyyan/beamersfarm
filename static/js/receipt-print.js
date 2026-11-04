document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-print]").forEach((button) => {
    button.addEventListener("click", () => {
      const hasCover = document.querySelector(".report-cover");
      const includeCover = !hasCover || window.confirm("Print with the Beamers Farms report cover page? Select Cancel to print the report without the cover page.");
      const hidden = hasCover && !includeCover;
      if (hidden) document.body.classList.add("hide-report-cover");
      const restore = () => { document.body.classList.remove("hide-report-cover"); window.removeEventListener("afterprint", restore); };
      window.addEventListener("afterprint", restore);
      window.print();
      window.setTimeout(restore, 1200);
    });
  });
});
