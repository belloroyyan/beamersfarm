document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('[data-checkout-form]');
  if (!form) return;
  const fields = [...form.querySelectorAll('input[required], select[required], textarea[required]')];
  const messageFor = (field) => {
    if (field.name === 'delivery_zone_id') return 'Choose a delivery area or pickup option.';
    if (field.name === 'address') return 'Add the delivery address for the selected zone.';
    if (field.name === 'phone') return 'Enter the phone number used for this order.';
    if (field.name === 'customer_name') return 'Enter your full name.';
    return 'Complete this field before placing the order.';
  };
  const validate = (field) => {
    const error = field.closest('label, .checkout-address-wrapper')?.querySelector('[data-field-error]') || form.querySelector(`#${field.id}-error`);
    const invalid = !field.checkValidity();
    field.setAttribute('aria-invalid', invalid ? 'true' : 'false');
    if (error) error.textContent = invalid ? messageFor(field) : '';
    return !invalid;
  };
  fields.forEach((field) => field.addEventListener('blur', () => validate(field)));
  form.addEventListener('submit', (event) => {
    const valid = fields.every(validate);
    if (!valid) {
      event.preventDefault();
      form.querySelector('[aria-invalid="true"]')?.focus();
      return;
    }
    const button = form.querySelector('[data-place-order]');
    if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); button.querySelector('span')?.replaceWith(document.createTextNode('…')); }
  });
});
