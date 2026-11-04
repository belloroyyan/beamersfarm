document.addEventListener("DOMContentLoaded", () => {
  const updatePaymentChoice = () => {
    document.querySelectorAll(".payment-choice").forEach((card) => {
      const input = card.querySelector('input[name="payment_method"]');
      card.classList.toggle("selected", Boolean(input && input.checked));
    });
  };

  document.querySelectorAll('input[name="payment_method"]').forEach((input) => {
    input.addEventListener("change", updatePaymentChoice);
  });
  updatePaymentChoice();
});
