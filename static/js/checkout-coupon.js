document.addEventListener("DOMContentLoaded", () => {
  const button = document.querySelector("[data-apply-coupon]");
  const input = document.querySelector('input[name="coupon_code"]');
  const zone = document.querySelector("[data-zone-select]");
  const status = document.querySelector("[data-coupon-live-status]");
  const discount = document.querySelector("[data-discount-output]");
  const total = document.querySelector("[data-total-output]");
  if (!button || !input || !status) return;

  const money = (value) => `₦${Number(value || 0).toLocaleString("en-NG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
  const csrf = button.dataset.csrf || window.CSRF_TOKEN || "";

  async function applyCoupon(suggestedCode = null) {
    if (suggestedCode !== null) input.value = suggestedCode;
    const code = input.value.trim().toUpperCase();
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    status.textContent = "Checking coupon…";
    status.className = "coupon-live-status";
    try {
      const body = new URLSearchParams({
        coupon_code: code,
        delivery_zone_id: zone?.value || "",
        _csrf_token: csrf,
      });
      const response = await fetch(button.dataset.validateUrl || window.COUPON_VALIDATE_URL, {
        method: "POST",
        headers: {
          "X-CSRF-Token": csrf,
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      });
      if (!response.ok) throw new Error(`Coupon validation returned ${response.status}`);
      const data = await response.json();
      if (data.ok) {
        status.textContent = `${data.message} Discount: ${money(data.discount)}. ${data.delivery_selected
          ? `Amount to pay: ${money(data.total)}.`
          : "Choose delivery or pickup to see the final amount."}`;
        status.classList.add("is-success");
        if (discount) discount.textContent = data.discount > 0 ? `-${money(data.discount)}` : "—";
        if (window.updateCheckoutDiscount) window.updateCheckoutDiscount(data.discount);
        else if (total && data.delivery_selected) total.textContent = money(data.total);
        document.querySelectorAll("[data-coupon-suggestion]").forEach((suggestion) => {
          suggestion.classList.toggle("is-selected", suggestion.dataset.couponSuggestion === code);
        });
      } else {
        status.textContent = data.message || "This coupon could not be applied.";
        status.classList.add("is-error");
        if (window.updateCheckoutDiscount) window.updateCheckoutDiscount(0);
        if (discount) discount.textContent = "—";
        document.querySelectorAll("[data-coupon-suggestion]").forEach((suggestion) => {
          suggestion.classList.remove("is-selected");
        });
      }
    } catch (_error) {
      status.textContent = "Coupon status could not be checked. Please try again.";
      status.classList.add("is-error");
    } finally {
      button.disabled = false;
      button.removeAttribute("aria-busy");
    }
  }

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      button.click();
    }
  });
  button.addEventListener("click", () => applyCoupon());
  document.querySelectorAll("[data-coupon-suggestion]").forEach((suggestion) => {
    suggestion.addEventListener("click", () => applyCoupon(suggestion.dataset.couponSuggestion || ""));
  });
});
