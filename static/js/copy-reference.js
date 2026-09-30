document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-copy-reference]').forEach((button) => {
    const status = button.parentElement.querySelector('.copy-reference-status');
    const originalLabel = button.textContent.trim();

    const fallbackCopy = (value) => {
      const field = document.createElement('textarea');
      field.value = value;
      field.setAttribute('readonly', '');
      field.style.position = 'fixed';
      field.style.opacity = '0';
      document.body.appendChild(field);
      field.select();
      const copied = document.execCommand('copy');
      field.remove();
      return copied;
    };

    button.addEventListener('click', async () => {
      const value = button.dataset.copyReference;
      let copied = false;
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(value);
          copied = true;
        } else {
          copied = fallbackCopy(value);
        }
      } catch (_error) {
        copied = fallbackCopy(value);
      }

      if (copied) {
        button.textContent = 'Copied';
        if (status) status.textContent = 'Order reference copied to clipboard.';
        window.setTimeout(() => { button.textContent = originalLabel; }, 1800);
      } else if (status) {
        status.textContent = 'Copy unavailable. Please select the order number and copy it manually.';
      }
    });
  });
});
