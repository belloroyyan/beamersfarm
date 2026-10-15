document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-share]").forEach((button) => {
    button.addEventListener("click", async () => {
      const data = {title: button.dataset.shareTitle || document.title, text: button.dataset.shareText || document.title, url: button.dataset.shareUrl || window.location.href};
      try {
        if (navigator.share) await navigator.share(data);
        else if (navigator.clipboard) { await navigator.clipboard.writeText(data.url); button.textContent = "Link copied"; setTimeout(() => button.textContent = "Share", 1800); }
      } catch (error) { if (error.name !== "AbortError") button.textContent = "Copy link"; }
    });
  });
});
