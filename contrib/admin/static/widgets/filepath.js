// filepath.js

// Helper for uploading files from FilePathWidget fields.

class FilePathUploader {
  constructor(editor, file, callbacks) {
    this.editor = editor;
    this.file = file;
    this.callbacks = callbacks || {};
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
        this.callbacks.success?.(body.url || body);
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
}

window.FilePathUploader = FilePathUploader;

// # The End

