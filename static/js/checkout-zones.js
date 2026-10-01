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
  refresh();
});
