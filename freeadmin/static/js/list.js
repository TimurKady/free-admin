// list.js
/**
 * Handle export button clicks and import form submissions on the admin list page.
 *
 * Version: 0.1.0
 * Author: Timur Kady
 * Email: timurkady@yandex.com
 */

class ListPage {
  constructor() {
    this.exportLinks = document.querySelectorAll('[aria-labelledby="exportMenu"] a');
    this.importForm = document.getElementById('import-form');
    this.importErrors = document.getElementById('import-errors');
    this.importModal = document.getElementById('importModal');
    this.bindEvents();
  }

  bindEvents() {
    this.exportLinks.forEach(link => link.addEventListener('click', e => this.handleExport(e)));
    this.importForm?.addEventListener('submit', e => this.handleImport(e));
  }

  selectedIds() {
    return Array.from(document.querySelectorAll('#tbody input[type="checkbox"]:checked')).map(cb => cb.value);
  }

  handleExport(event) {
    event.preventDefault();
    const url = event.currentTarget.getAttribute('href');
    const ids = this.selectedIds();
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = url;
    ids.forEach(id => {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'ids';
      input.value = id;
      form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
  }

  async handleImport(event) {
    event.preventDefault();
    if (!this.importForm) return;
    this.importErrors.textContent = '';
    const url = `${window.location.pathname}import`;
    const fileInput = document.getElementById('import-file');
    if (!fileInput.files.length) {
      this.importErrors.textContent = 'No file selected';
      return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    const dry = document.getElementById('import-dry-run').checked ? '1' : '0';
    formData.append('dry', dry);
    try {
      const resp = await fetch(url, { method: 'POST', body: formData });
      const data = await resp.json();
      if (!resp.ok) {
        this.importErrors.textContent = data.detail || 'Import failed';
        return;
      }
      this.importForm.reset();
      const modal = bootstrap.Modal.getInstance(this.importModal);
      modal?.hide();
    } catch (err) {
      this.importErrors.textContent = err.message;
    }
  }
}

new ListPage();

// # The End

