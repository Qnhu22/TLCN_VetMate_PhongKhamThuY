(() => {
  'use strict';
  const rows = document.getElementById('prescription-rows');
  const add = document.getElementById('add-prescription-row');
  if (!rows || !add) return;
  function renumber() {
    rows.querySelectorAll('.rx-row').forEach((row, i) => {
      row.querySelector('legend').textContent = `Thuốc ${i + 1}`;
      row.querySelector('[data-remove-rx]').disabled = rows.children.length <= 1;
    });
    add.disabled = rows.children.length >= 30;
  }
  add.addEventListener('click', () => {
    if (rows.children.length >= 30) return;
    const row = rows.firstElementChild.cloneNode(true);
    row.querySelectorAll('input, textarea, select').forEach(input => { input.value = ''; });
    rows.appendChild(row);
    renumber();
    row.querySelector('select').focus();
  });
  rows.addEventListener('click', event => {
    const button = event.target.closest('[data-remove-rx]');
    if (button && rows.children.length > 1) { button.closest('.rx-row').remove(); renumber(); }
  });
  renumber();
})();
