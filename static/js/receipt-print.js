document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-print]').forEach((button) => {
    button.addEventListener('click', () => {
      const hasCover = document.querySelector('.report-overall-cover, .report-cover');
      if (!hasCover) { window.print(); return; }
      let dialog = document.querySelector('[data-cover-print-dialog]');
      if (!dialog) {
        dialog = document.createElement('dialog'); dialog.className = 'staff-report-print-dialog'; dialog.setAttribute('data-cover-print-dialog', '');
        dialog.innerHTML = '<button type="button" class="admin-dialog-x" data-cover-close aria-label="Close">×</button><p class="eyebrow">Report printing</p><h2>Include the cover report?</h2><p class="form-note">Choose whether the Beamers Farms cover page should be printed with this report.</p><div class="form-actions"><button type="button" class="button button-outline" data-cover-no>Report only</button><button type="button" class="button button-dark" data-cover-yes>Include cover</button></div>';
        document.body.appendChild(dialog);
      }
      const print = (include) => { dialog.close(); document.body.classList.toggle('print-with-cover', include); document.body.classList.toggle('hide-report-cover', !include); const restore=()=>{document.body.classList.remove('print-with-cover','hide-report-cover');window.removeEventListener('afterprint',restore);}; window.addEventListener('afterprint',restore); window.print(); window.setTimeout(restore,1200); };
      dialog.querySelector('[data-cover-yes]').onclick=()=>print(true); dialog.querySelector('[data-cover-no]').onclick=()=>print(false); dialog.querySelector('[data-cover-close]').onclick=()=>dialog.close(); dialog.showModal();
    });
  });
});
