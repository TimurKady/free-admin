// filepath.js

// Helper for uploading files from FilePathWidget fields.

class FilePathUploader {
  constructor(editor, file, callbacks) {
    this.editor = editor;
    this.file = file;
    this.callbacks = callbacks || {};
  }

  _updateLink(url) {
    const prefix = this.editor?.schema?.options?.upload?.media_prefix || '/media/';
    const base = prefix.replace(/\/$/, '');
    const input = this.editor?.input;
    const parent = input && input.parentNode;

    let link = null;
    if (parent) {
      const links = parent.querySelectorAll('a');
      link = links[0] || null;
      for (let i = 1; i < links.length; i++) {
        links[i].remove();
      }
    }

    if (!url) {
      if (this.editor?.schema) {
        this.editor.schema.links = [];
      }
      if (link) {
        link.remove();
      }
      return;
    }

    const href = `${base}/${url}`.replace(/\/{2,}/g, '/');
    const text = url.replace(/^\/+/, '');

    if (this.editor?.schema) {
      this.editor.schema.links = [{ href, title: text }];
    }

    if (link) {
      link.setAttribute('data-filepath-link', '1');
      link.href = href;
      link.target = '_blank';
    
      // превращаем ссылку в кнопку
      link.textContent = 'View';
      link.classList.add('btn', 'btn-secondary', 'btn-sm');
      link.setAttribute('role', 'button');
      link.title = text.split('/').pop();
    }
  }

  send() {
    const url = this.editor?.schema?.options?.upload?.endpoint;
    if (!url) {
      this.callbacks.failure?.('Missing upload endpoint');
      return;
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.withCredentials = true;

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        let body = {};
        try { body = JSON.parse(xhr.responseText); } catch {}
        const urlVal = body.url || body;
        if (urlVal) {
          this._updateLink(urlVal);
        }
        this.callbacks.success?.(urlVal);
      } else {
        this.callbacks.failure?.(xhr.statusText || 'Upload failed');
      }
    };

    xhr.onerror = () => this.callbacks.failure?.('Network error');

    if (xhr.upload && typeof this.callbacks.updateProgress === 'function') {
      xhr.upload.onprogress = evt => {
        if (evt.lengthComputable) {
          this.callbacks.updateProgress(evt.loaded / evt.total);
        }
      };
    }

    const formData = new FormData();
    formData.append('file', this.file);
    xhr.send(formData);
  }

  static inject(schema) {
    if (!schema || typeof schema !== 'object') return;
    if (schema.upload_endpoint && schema.options && schema.options.upload) {
      schema.options.upload.endpoint = schema.upload_endpoint;
    }
    if (schema.properties) {
      Object.values(schema.properties).forEach(s => FilePathUploader.inject(s));
    }
    if (schema.items) {
      FilePathUploader.inject(schema.items);
    }
  }

  static init(schema) {
    JSONEditor.defaults = JSONEditor.defaults || {};
    JSONEditor.defaults.callbacks = JSONEditor.defaults.callbacks || {};
    JSONEditor.defaults.callbacks.upload = JSONEditor.defaults.callbacks.upload || {};
    JSONEditor.defaults.callbacks.upload.FilePathUploader = function (jseditor, type, file, cbs) {

      if (!(file instanceof File)) {
        cbs?.failure?.('Invalid file object');
        return;
      }
      new FilePathUploader(jseditor, file, cbs).send();
    };
    FilePathUploader.inject(schema);
  }

  static updateExistingLinks(rootEditor) {
    const editors = rootEditor?.editors || {};
    Object.values(editors).forEach(ed => {
      const handler = ed?.schema?.options?.upload?.upload_handler;
      if (handler !== 'FilePathUploader') return;
      let val = typeof ed?.getValue === 'function' ? ed.getValue() : null;
      if (typeof val !== 'string' || !val) return;
      const prefix = ed?.schema?.options?.upload?.media_prefix || '/media/';
      if (val.startsWith(prefix)) {
        val = val.slice(prefix.length).replace(/^\/+/, '');
        if (typeof ed?.setValue === 'function') {
          ed.setValue(val);
        }
      }
      new FilePathUploader(ed, null, {})._updateLink(val);
    });
  }
}

window.FilePathUploader = FilePathUploader;

// # The End
