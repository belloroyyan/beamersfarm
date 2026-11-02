document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-print]").forEach((button) => {
    button.addEventListener("click", () => {
      const hasOverallCover = Boolean(document.querySelector(".report-overall-cover"));
      const includeCover = hasOverallCover
        ? window.confirm(
            "Include the overall Beamers Farm Operations Report cover at the front?\n\n" +
            "Choose OK to include the overall cover, or Cancel to print this section without it."
          )
        : false;

      const cleanup = () => {
        document.body.classList.remove("print-with-cover");
        document.documentElement.classList.remove("print-with-cover");
      };

      // Apply the print state before the browser captures its print layout.
      document.body.classList.toggle("print-with-cover", includeCover);
      document.documentElement.classList.toggle("print-with-cover", includeCover);

      window.addEventListener("afterprint", cleanup, { once: true });

      // A frame boundary lets Chrome/Edge commit the class and print CSS
      // before opening the print preview.
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => window.print());
      });

      // Fallback for browsers that omit afterprint when printing is cancelled.
      window.setTimeout(cleanup, 30000);
    });
  });
});
