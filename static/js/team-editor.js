(() => {
  'use strict';

  const init = () => {
    const dialog = document.querySelector('[data-team-member-dialog]');
    const rows = document.querySelector('#team-rows');
    const empty = document.querySelector('[data-team-empty]');
    const count = document.querySelector('[data-team-member-count]');
    const opener = document.querySelector('[data-open-team-member-dialog]');
    if (!dialog || !rows || !opener) return;

    const field = (name) => dialog.querySelector(`[data-new-member-${name}]`);
    const select = dialog.querySelector('[data-new-staff-select]');
    const closeDialog = () => {
      if (typeof dialog.close === 'function') dialog.close();
      else dialog.removeAttribute('open');
    };
    const openDialog = () => {
      reset();
      try {
        if (typeof dialog.showModal === 'function') dialog.showModal();
        else dialog.setAttribute('open', '');
      } catch (error) {
        // A stale open state should never make the button appear unresponsive.
        dialog.setAttribute('open', '');
        console.warn('Team member dialog fallback opened:', error);
      }
    };
    const update = () => {
      const total = rows.querySelectorAll('[data-team-row]').length;
      if (count) count.textContent = `${total} member${total === 1 ? '' : 's'}`;
      if (empty) empty.hidden = total > 0;
      rows.querySelectorAll('[data-team-row]').forEach((row, index) => {
        const label = row.querySelector('.team-row-toolbar strong');
        if (label) label.textContent = `Team member ${index + 1}`;
      });
    };
    const reset = () => {
      if (select) select.value = '';
      ['name', 'role', 'photo', 'bio'].forEach((key) => {
        const input = field(key);
        if (input) input.value = '';
      });
    };
    const addRow = () => {
      const nameInput = field('name');
      const name = nameInput?.value.trim() || '';
      if (!name) {
        nameInput?.focus();
        return;
      }
      const row = document.createElement('div');
      row.className = 'team-row';
      row.dataset.teamRow = '';
      row.innerHTML = `<input type="hidden" name="staff_id" value="">
        <div class="team-row-toolbar"><strong></strong><button class="text-button team-remove-button" type="button" data-remove-team-member>Remove</button></div>
        <div class="team-row-fields">
          <label>Public name<input name="name" maxlength="120" required></label>
          <label>Role<input name="role" maxlength="80" placeholder="e.g. Founder, Operations"></label>
          <label class="team-row-wide">Photo URL<input name="photo" maxlength="500" placeholder="Optional image URL"></label>
          <label class="team-row-wide">Short bio<textarea name="bio" rows="3" maxlength="400" placeholder="Optional introduction"></textarea></label>
        </div>`;
      row.querySelector('[name="staff_id"]').value = select?.value || '';
      row.querySelector('[name="name"]').value = name;
      row.querySelector('[name="role"]').value = field('role')?.value || '';
      row.querySelector('[name="photo"]').value = field('photo')?.value || '';
      row.querySelector('[name="bio"]').value = field('bio')?.value || '';
      rows.appendChild(row);
      update();
      reset();
      closeDialog();
    };

    opener.addEventListener('click', (event) => {
      event.preventDefault();
      openDialog();
    });
    dialog.querySelectorAll('[data-close-team-member-dialog]').forEach((button) => {
      button.addEventListener('click', closeDialog);
    });
    dialog.querySelector('[data-add-team-member]')?.addEventListener('click', addRow);
    select?.addEventListener('change', () => {
      const option = select.options[select.selectedIndex];
      const nameInput = field('name');
      if (option?.dataset.name && nameInput && !nameInput.value.trim()) nameInput.value = option.dataset.name;
    });
    rows.addEventListener('click', (event) => {
      const button = event.target.closest('[data-remove-team-member]');
      if (button) {
        button.closest('[data-team-row]')?.remove();
        update();
      }
    });
    update();
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
