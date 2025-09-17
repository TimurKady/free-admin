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
    if (!link && parent) {
      link = document.createElement('a');
      parent.appendChild(link);
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
    const globalObj = typeof window !== 'undefined' ? window : globalThis;
    const manager = FilePathUploaderManager.bootstrap(globalObj);
    return manager.legacyInit(schema);
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

class FilePathUploaderManager {
  constructor(globalObj) {
    this.global = globalObj;
    this._callbackRegistered = false;
    this._processedEditors = new WeakSet();
    this._handleSchemaEvent = this._handleSchemaEvent.bind(this);
    this._handleCreatedEvent = this._handleCreatedEvent.bind(this);
    this._handleReadyEvent = this._handleReadyEvent.bind(this);
    this.readyPromise = this._waitForJSONEditor();
    this.readyPromise.then((JSONEditorGlobal) => {
      this._registerUploadCallback(JSONEditorGlobal);
    });

    if (this.global.JSONEditor) {
      this._registerUploadCallback(this.global.JSONEditor);
    }

    const doc = this.global.document;
    if (doc?.addEventListener) {
      doc.addEventListener('admin:jsoneditor:schema', this._handleSchemaEvent);
      doc.addEventListener('admin:jsoneditor:created', this._handleCreatedEvent);
      doc.addEventListener('admin:jsoneditor:ready', this._handleReadyEvent);
    }
  }

  static bootstrap(globalObj) {
    if (!this.instance) {
      this.instance = new FilePathUploaderManager(globalObj);
    }
    return this.instance;
  }

  _waitForJSONEditor() {
    if (this.global.JSONEditor) {
      return Promise.resolve(this.global.JSONEditor);
    }
    return new Promise(resolve => {
      const check = () => {
        if (this.global.JSONEditor) {
          resolve(this.global.JSONEditor);
        } else {
          this.global.setTimeout(check, 50);
        }
      };
      check();
    });
  }

  _registerUploadCallback(JSONEditorGlobal) {
    if (this._callbackRegistered || !JSONEditorGlobal) return;
    JSONEditorGlobal.defaults = JSONEditorGlobal.defaults || {};
    JSONEditorGlobal.defaults.callbacks = JSONEditorGlobal.defaults.callbacks || {};
    JSONEditorGlobal.defaults.callbacks.upload = JSONEditorGlobal.defaults.callbacks.upload || {};
    JSONEditorGlobal.defaults.callbacks.upload.FilePathUploader = function (jseditor, type, file, cbs) {
      if (!(file instanceof File)) {
        cbs?.failure?.('Invalid file object');
        return;
      }
      new FilePathUploader(jseditor, file, cbs).send();
    };
    this._callbackRegistered = true;
  }

  _handleSchemaEvent(event) {
    const schema = event?.detail?.schema;
    if (schema) {
      FilePathUploader.inject(schema);
    }
    const JSONEditorGlobal = this.global.JSONEditor;
    if (JSONEditorGlobal) {
      this._registerUploadCallback(JSONEditorGlobal);
    }
  }

  _handleCreatedEvent(event) {
    const editor = event?.detail?.editor;
    if (!editor) return;
    if (typeof editor.on === 'function') {
      editor.on('ready', () => this._handleEditorReady(editor));
    } else {
      this._handleEditorReady(editor);
    }
  }

  _handleReadyEvent(event) {
    const editor = event?.detail?.editor;
    if (!editor) return;
    this._handleEditorReady(editor);
  }

  _handleEditorReady(editor) {
    if (!editor || this._processedEditors.has(editor)) {
      return;
    }
    this._processedEditors.add(editor);
    FilePathUploader.updateExistingLinks(editor);
  }

  async legacyInit(schema) {
    if (schema) {
      FilePathUploader.inject(schema);
    }
    const JSONEditorGlobal = await this.readyPromise;
    this._registerUploadCallback(JSONEditorGlobal);
  }
}

FilePathUploaderManager.instance = null;

const filePathGlobalObj = typeof window !== 'undefined' ? window : globalThis;
FilePathUploaderManager.bootstrap(filePathGlobalObj);
filePathGlobalObj.FilePathUploader = FilePathUploader;


// # The End
