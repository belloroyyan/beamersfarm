(() => {
  const copyText = async (value) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
      return true;
    }
    const field = document.createElement('textarea');
    field.value = value;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed'; field.style.opacity = '0'; field.style.pointerEvents = 'none';
    document.body.appendChild(field); field.select(); field.setSelectionRange(0, field.value.length);
    const copied = document.execCommand('copy'); field.remove();
    if (!copied) throw new Error('Copy command was not available');
    return true;
  };

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-copy-account]');
    if (!button) return;
    const original = button.dataset.copyLabel || 'Copy account number';
    const value = String(button.dataset.copyAccount || '').trim();
    if (!value) return;
    button.disabled = true;
    try {
      await copyText(value);
      button.textContent = 'Copied!';
      button.classList.add('is-copied');
    } catch (_) {
      button.textContent = 'Select number to copy';
      const number = button.closest('.bank-account-card')?.querySelector('.bank-card-number');
      if (number) { const range = document.createRange(); range.selectNodeContents(number); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); }
    }
    window.setTimeout(() => { button.textContent = original; button.disabled = false; button.classList.remove('is-copied'); }, 2200);
  });

  document.addEventListener('click', (event) => {
    const link = event.target.closest('[data-wa-help]');
    if (!link) return;
    const message = [
      '*Dear Beamers Farms,*', '',
      '• What happened / What I need: [State your issue or request]',
      '• Key Details:',
      '  - Account / Order ID: [Insert number, if applicable]',
      '  - Date of issue: [Insert date]',
      '• What I would like: [State the solution you want]', '',
      'Thank you for your help.'
    ].join('\n');
    link.href = `https://wa.me/2348129944488?text=${encodeURIComponent(message)}`;
  });
})();
