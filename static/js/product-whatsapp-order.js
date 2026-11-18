(() => {
  const init = () => document.querySelectorAll('[data-whatsapp-product-order]').forEach((button) => {
    const input = document.querySelector('.quantity-form input[name="quantity"]');
    const name = button.dataset.productName || 'Product';
    const unit = button.dataset.productUnit || 'unit';
    const fallback = Number(button.dataset.defaultQuantity || 1);
    const update = () => {
      const raw = input ? Number(input.value) : fallback;
      const qty = Number.isFinite(raw) && raw > 0 ? raw : fallback;
      const message = [
        'Hello Beamers Farms, I would like to place an order:', '',
        `- Item Name / Description: ${name}`,
        `- Quantity: ${qty} ${unit}`,
        '- Delivery To: ', '',
        'Please send me the total price and bank details to proceed with payment. Thanks!'
      ].join('\n');
      button.href = `https://wa.me/2348129944488?text=${encodeURIComponent(message)}`;
    };
    input?.addEventListener('input', update); input?.addEventListener('change', update); update();
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true }); else init();
})();
