document.addEventListener("DOMContentLoaded", () => {
  const select = document.querySelector("[data-zone-select]");
  if (!select) return;

  const feeOutput = document.querySelector("[data-delivery-fee-output]");
  const totalOutput = document.querySelector("[data-total-output]");
  const note = document.querySelector("[data-zone-fee-note]");
  const addressWrap = document.querySelector("[data-delivery-address-wrap]");
  const address = document.querySelector("#delivery-address");
  const pickupCard = document.querySelector("[data-pickup-address]");
  const disclaimer = document.querySelector("[data-zone-address-disclaimer]");
  const zoneDescription = document.querySelector("[data-zone-description]");
  const subtotal = Number(select.dataset.subtotal || 0);
  const money = (value) => `₦${Number(value).toLocaleString("en-NG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const locationSearch = document.querySelector("[data-location-search]");
  const locationMatch = document.querySelector("[data-location-match]");
  const zoneOptions = Array.from(select.options).filter((option) => option.value);
  const normalize = (value) => (value || "").toLowerCase().replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();

  const selectZone = (option) => {
    select.value = option.value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const showLocationMatches = () => {
    if (!locationSearch || !locationMatch) return;
    const query = normalize(locationSearch.value);
    if (!query) {
      locationMatch.hidden = true;
      locationMatch.innerHTML = "";
      return;
    }
    const words = query.split(" ").filter((word) => word.length > 1);
    const matches = zoneOptions.map((option) => {
      const haystack = normalize(option.dataset.search || option.textContent);
      const score = words.reduce((total, word) => total + (haystack.includes(word) ? 1 : 0), 0);
      return { option, score };
    }).filter((item) => item.score > 0).sort((a, b) => b.score - a.score);
    locationMatch.hidden = false;
    if (!matches.length) {
      locationMatch.innerHTML = "<strong>No configured zone matched that search.</strong><span>Choose a delivery option below or contact Beamers Farm to confirm your area.</span>";
      return;
    }
    const bestScore = matches[0].score;
    const best = matches.filter((item) => item.score === bestScore).slice(0, 3);
    locationMatch.innerHTML = `<strong>Possible match${best.length > 1 ? "es" : ""}</strong><div class="location-match-list">${best.map(({ option }) => `<button type="button" class="location-match-button" data-zone-match="${option.value}">${option.textContent.trim()}</button>`).join("")}</div>`;
    locationMatch.querySelectorAll("[data-zone-match]").forEach((button) => {
      button.addEventListener("click", () => {
        const option = zoneOptions.find((candidate) => candidate.value === button.dataset.zoneMatch);
        if (option) {
          selectZone(option);
          locationSearch.value = option.textContent.trim().replace(/ · .*/, "");
          locationMatch.hidden = true;
        }
      });
    });
    if (best.length === 1) selectZone(best[0].option);
  };

  const refresh = () => {
    const option = select.options[select.selectedIndex];
    const chosen = Boolean(option && option.value);
    const pickup = chosen && option.dataset.isPickup === "true";
    const fee = chosen ? Number(option.dataset.fee || 0) : 0;
    if (zoneDescription) {
      zoneDescription.textContent = chosen && !pickup ? (option.dataset.description || "") : "";
      zoneDescription.hidden = !chosen || pickup || !option.dataset.description;
    }
    if (feeOutput) feeOutput.textContent = chosen ? money(fee) : "Choose an option";
    if (totalOutput) totalOutput.textContent = chosen ? money(subtotal + fee) : "Choose an option";
    if (addressWrap) addressWrap.hidden = !chosen || pickup;
    if (address) address.required = chosen && !pickup;
    if (pickupCard) pickupCard.hidden = !pickup;
    if (disclaimer) disclaimer.hidden = !chosen || pickup;
    if (note) {
      note.textContent = !chosen
        ? "Choose a delivery area or free pickup option to calculate the amount due now."
        : pickup
          ? "Farm pickup has no delivery fee. Payment is still required before the owner confirms the order."
          : "The selected delivery fee is included in the amount due now. The entered address will be checked against this zone.";
    }
  };

  select.addEventListener("change", refresh);
  if (locationSearch) locationSearch.addEventListener("input", showLocationMatches);
  refresh();
});
