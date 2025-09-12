// static/widgets/barcode-editor.js

class JSONEditorInitializer {
  static ready = null;

  constructor(globalObj) {
    this.global = globalObj;
    if (!JSONEditorInitializer.ready) {
      JSONEditorInitializer.ready = this.init();
    }
  }

  async init() {
    await this._waitForLibraries();
    if (this.global.JSONEditor && this.global.JsBarcode) {
      this.registerEditor();
    } else {
      console.error('Required libraries are not defined. BarCodeEditor cannot be initialized.');
    }
  }

  _waitForLibraries() {
    return new Promise(resolve => {
      const check = () => {
        if (this.global.JSONEditor && this.global.JsBarcode) {
          resolve();
        } else {
          this.global.setTimeout(check, 50);
        }
      };
      check();
    });
  }

  registerEditor() {
    const JSONEditorGlobal = this.global.JSONEditor;
    const globalObj = this.global;
    class BarCodeEditor extends JSONEditorGlobal.defaults.editors.string {
      build() {
        super.build();

        this.global = globalObj;

        const opts = (this.schema.options && this.schema.options.options) || {};
        this.__barcodeOptions = Object.assign({ format: 'code128', displayValue: true }, opts);

        this.barcodeEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.barcodeEl.setAttribute('aria-label', 'BarCode');
        this.barcodeEl.style.marginTop = '0.25rem';
        if (typeof this.__barcodeOptions.height === 'number') {
          this.barcodeEl.style.height = `${this.__barcodeOptions.height}px`;
        }
        const showInput = !this.schema.options || this.schema.options.show_input !== false;
        if (!showInput && this.input && this.input.parentNode) {
          this.input.style.display = 'none';
        }

        const holder =
          this.control ||
          this.container ||
          (this.input && this.input.parentNode) ||
          this.theme?.getContainer?.();
        if (holder) {
          holder.appendChild(this.barcodeEl);
        }
        this._originalDescription = this.description ? this.description.textContent : '';
        this._renderBarcode();
      }

      setValue(val, initial, fromTemplate) {
        const changed = super.setValue(val, initial, fromTemplate);
        this._renderBarcode();
        return changed;
      }

      enable() {
        super.enable();
        this._renderBarcode();
      }

      disable(alwaysDisabled) {
        super.disable(alwaysDisabled);
        this._renderBarcode();
      }

      _renderBarcode() {
        if (!this.barcodeEl) return;

        const val = this.getValue();
        if (!val) {
          this.barcodeEl.innerHTML = '';
          this.barcodeEl.style.display = 'none';
          return;
        }

        const JsBarcodeLib = this.global && this.global.JsBarcode;
        if (!JsBarcodeLib) {
          this._showBarcodeError('JsBarcode library is not loaded.');
          return;
        }

        try {
          JsBarcodeLib(this.barcodeEl, val, this.__barcodeOptions);
          this.barcodeEl.style.display = '';
          if (this.description) {
            this.description.textContent = this._originalDescription;
          }
        } catch (e) {
          this._showBarcodeError('Barcode render error: ' + (e && e.message ? e.message : e));
        }
      }

      _showBarcodeError(msg) {
        this.barcodeEl.innerHTML = '';
        this.barcodeEl.style.display = 'none';
        if (!this.description) {
          this.description = document.createElement('p');
          this.control.appendChild(this.description);
        }
        this.description.textContent = msg;
      }
    }

    JSONEditorGlobal.defaults.resolvers.unshift(
      schema => schema?.options?.widget === 'barcode' && 'barcode'
    );
    JSONEditorGlobal.defaults.editors.barcode = BarCodeEditor;
  }
}

new JSONEditorInitializer(globalThis);

// # The End

