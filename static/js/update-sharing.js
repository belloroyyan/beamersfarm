(() => {
  const copyText = async (value) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
      return;
    }
    const field = document.createElement("textarea");
    field.value = value;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    const copied = document.execCommand("copy");
    field.remove();
    if (!copied) throw new Error("Clipboard access is not available.");
  };

  document.querySelectorAll("[data-update-share]").forEach((card) => {
    const url = card.dataset.shareUrl;
    const imageUrl = card.dataset.shareImage;
    const title = card.dataset.shareTitle || "Beamers Farm update";
    const text = `${card.dataset.shareText || title}\n${url}`;
    const status = card.querySelector("[data-share-status]");

    card.querySelector("[data-share-update]")?.addEventListener("click", async () => {
      if (navigator.share) {
        try {
          await navigator.share({ title, text, url });
          if (status) status.textContent = "Update link shared.";
        } catch (error) {
          if (error.name !== "AbortError" && status) {
            status.textContent = "Sharing was unavailable. Download the image or copy the link instead.";
          }
        }
        return;
      }
      try {
        await copyText(url);
        if (status) status.textContent = "Link copied. Download the image to post it as a picture.";
      } catch (_) {
        if (status) status.textContent = "Use Download image to save the card, or copy the page address from your browser.";
      }
    });

    card.querySelector("[data-share-image-button]")?.addEventListener("click", async () => {
      if (!navigator.share || !navigator.canShare || typeof File === "undefined") {
        if (status) status.textContent = "Direct image sharing is not supported here. Use Download image to post the PNG.";
        return;
      }
      try {
        const response = await fetch(imageUrl, { credentials: "same-origin" });
        if (!response.ok) throw new Error("The update image could not be loaded.");
        const imageFile = new File([await response.blob()], `${title.slice(0, 48).replace(/[^a-z0-9_-]+/gi, "-") || "beamers-update"}.png`, { type: "image/png" });
        if (!navigator.canShare({ files: [imageFile] })) {
          if (status) status.textContent = "This browser cannot attach images to shares. Use Download image to post the PNG.";
          return;
        }
        await navigator.share({ title, text, files: [imageFile] });
        if (status) status.textContent = "Update image shared.";
      } catch (error) {
        if (error.name !== "AbortError" && status) {
          status.textContent = "Image sharing did not complete. Use Download image or Share update instead.";
        }
      }
    });

    card.querySelector("[data-copy-update-link]")?.addEventListener("click", async () => {
      try {
        await copyText(url);
        if (status) status.textContent = "Update link copied.";
      } catch (_) {
        if (status) status.textContent = "Clipboard access is unavailable. Copy the page address from your browser.";
      }
    });
  });
})();
