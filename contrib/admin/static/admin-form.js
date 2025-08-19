// admin-form.js

// API endpoints injected via templates (see contrib/admin/core/settings)
const { prefix: API_PREFIX, uiconfig: API_UICONFIG } = window.ADMIN_API;

class AdminFormEditor {
  constructor({ rootId = 'form-root', spinnerId = 'form-spinner', app, model, pk, prefix, config = {} }) {
    this.root = document.getElementById(rootId);
    this.spinner = document.getElementById(spinnerId);
    this.pk = pk;
    this.mode = pk ? 'edit' : 'add';
    this.prefix = prefix;

    this.base = window.location.pathname.replace(/\/(add|[^/]+\/edit)\/?$/, '');
    const parts = this.base.split('/').filter(Boolean);
    this.model = model || parts.pop();
    this.app = app || parts.pop();

    this.cfg = Object.assign({
      defaults: {
        theme: 'bootstrap5',
        iconlib: 'bootstrap',
        display_required_only: false,
        disable_edit_json: true,
        disable_collapse: true,
        show_errors: 'interaction',
        required_by_default: false,
        expand_height: true,
        disable_properties: true,
        no_additional_properties: true,
        show_opt_in: false,
        form_name_root: '\u200B',
        remove_empty_properties: false,
      },
      endpoints: {
        schema: (mode, pk) => `${this.base}/_schema?mode=${mode}` + (pk ? `&pk=${pk}` : ''),
        uiconfig: (p, a, m) => `${p}${API_UICONFIG}?app=${a}&model=${m}`,
        save: (base, pk) => pk ? `${base}/${pk}` : base
      },
      debug: false,
    }, config);
  }

  async load() {
    try {
      const { schema, startval, uiSchema } = await this.fetchSchemaUi();

      this.bakeUiIntoSchema(schema, uiSchema);

      let sv = startval;
      if (sv === null || typeof sv !== 'object') {
        sv = {};
      }
      if (schema && typeof schema === 'object' && schema.type === 'object' && schema.additionalProperties === undefined) {
        schema.additionalProperties = false;
      }

      this.spinner.style.display = 'none';

      this.editor = new JSONEditor(this.root, {
        schema,
        startval: sv,
        ...this.cfg.defaults,
      });

      window._editor = this.editor;

      this.hideRootHeader();
      this.bindSubmit();

    } catch (err) {
      console.error(err);
      alert('Failed to load form.');
    }
  }

  // Статически переносим настройки из uiSchema в JSON-Schema
  bakeUiIntoSchema(schema, ui) {
    if (!schema || !schema.properties || !ui) return;

    // 2.1 Порядок полей (ui:order)
    const order = ui['ui:order'];
    if (Array.isArray(order)) {
      order.forEach((name, idx) => {
        if (schema.properties[name]) {
          schema.properties[name].propertyOrder = idx;
        }
      });
    }

    // 2.2 Пробег по полям 1-го уровня
    for (const [field, cfg] of Object.entries(ui)) {
      if (field.startsWith('ui:')) continue;
      const ps = schema.properties[field];
      if (!ps || !cfg) continue;

      // readonly -> в схему
      if (cfg['ui:readonly']) {
        ps.readOnly = true;
        ps.options = Object.assign({}, ps.options, {
          input_attributes: Object.assign(
            {},
            ps.options?.input_attributes,
            { readonly: true, disabled: true }
          )
        });
      }

      // widget -> только встроенные мапим в схему (статично)
      const w = cfg['ui:widget'];
      if (w === 'textarea') {
        if (ps.type === 'string') ps.format = 'textarea';
      } else if (w === 'hidden') {
        if (ps.type === 'string') {
          ps.format = 'hidden';
        } else {
          ps.options = Object.assign({}, ps.options, { hidden: true });
        }
      }

      // ui:options -> прокинем в schema.options (статично)
      if (cfg['ui:options'] && typeof cfg['ui:options'] === 'object') {
        ps.options = Object.assign({}, ps.options, cfg['ui:options']);
      }
    }
  }

  async fetchSchemaUi() {
    const sURL = this.cfg.endpoints.schema(this.mode, this.pk);
    const uURL = this.cfg.endpoints.uiconfig(this.prefix, this.app, this.model);
    const [sRes, uRes] = await Promise.all([fetch(sURL), fetch(uURL)]);
    if (!sRes.ok) throw new Error(await sRes.text());
    if (!uRes.ok) throw new Error(await uRes.text());

    const { schema, startval } = await sRes.json();
    const { uiSchema } = await uRes.json();
    this.filterUiBySchema(uiSchema, schema);
    return { schema, startval, uiSchema };
  }

  filterUiBySchema(ui, schema) {
    if (!ui) return;
    for (const k of Object.keys(ui)) {
      if (!k.startsWith('ui:') && !schema?.properties?.[k]) delete ui[k];
    }
  }

  hideRootHeader() {
    const rootEditor = this.editor.getEditor('root');
    if (rootEditor?.header) rootEditor.header.style.display = 'none';
  }

  showBanner(text, variant = 'warning') {
    const host = this.root.parentElement;
    let el = host.querySelector('.form-alert-host');
    if (!el) {
      el = document.createElement('div');
      el.className = 'form-alert-host my-2';
      host.prepend(el);
    }
    if (!text) { el.innerHTML = ''; return; }
    el.innerHTML = `<div class="alert alert-${variant} py-2 mb-2">${text}</div>`;
  }

  applyServerErrors(detail) {
    if (detail && typeof detail.detail === 'string') {
      this.showBanner(detail.detail, 'warning');
    }

    const errsMap = (detail && detail.errors) || {};
    const list = Object.entries(errsMap).map(([field, msg]) => ({
      path: `root.${field}`,
      message: String(msg ?? 'Invalid value'),
    }));
    if (!list.length) return false;

    this.editor.showValidationErrors(list);

    // Точечный сброс подсветки: при вводе в поле с ошибкой — убираем его из внешних ошибок
    list.forEach(({ path }) => {
      const ed = this.editor.getEditor(path);
      const holder = ed?.container || ed?.theme?.container || null;
      if (!holder) return;
      const handler = () => {
        const rest = (this._extErrors || []).filter(e => e.path !== path);
        this._extErrors = rest;
        this.editor.showValidationErrors(rest);
        holder.removeEventListener('input', handler, true);
        if (!rest.length) this.showBanner('');
      };
      holder.addEventListener('input', handler, true);
    });
    this._extErrors = list;

    const firstPath = list[0].path;
    if (typeof this.editor.scrollTo === 'function') this.editor.scrollTo(firstPath);
    const firstEd = this.editor.getEditor(firstPath);
    firstEd?.activate?.();
    try { firstEd?.input?.focus?.(); } catch {}

    return true;
  }

  bindSubmit() {
    const btn = document.getElementById('submit');
    btn?.addEventListener('click', () => this.onSubmit());
  }

  async onSubmit() {
    const btn = document.getElementById('submit');
    btn?.setAttribute('disabled', 'disabled');
    this.editor.showValidationErrors([]);
    this._extErrors = [];
    this.showBanner('');

    const errs = this.editor.validate();
    if (errs.length) {
      const ext = errs.map(e => ({ path: e.path, message: e.message }));
      this.editor.showValidationErrors(ext);
      if (ext[0]?.path && typeof this.editor.scrollTo === 'function') {
        this.editor.scrollTo(ext[0].path);
      }
      btn?.removeAttribute('disabled');
      return;
    }

    const value = this.editor.getValue();
    const cleanedValue = this.cleanEmptyValues(value);

    const url = this.cfg.endpoints.save(this.base, this.pk);
    const method = this.pk ? 'PUT' : 'POST';

    try {
      const resp = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(cleanedValue),
      });

      if (!resp.ok) {
        if (resp.status === 422) {
          let data; try { data = await resp.json(); } catch {}
          const handled = this.applyServerErrors(data?.detail || data);
          if (handled) { btn?.removeAttribute('disabled'); return; }
        }
        const txt = await resp.text();
        alert('Save error: ' + txt);
        btn?.removeAttribute('disabled');
        return;
      }
      window.location.href = `${this.base}/`;
    } catch (err) {
      console.error(err);
      alert('Network error during save.');
      btn?.removeAttribute('disabled');
    }
  }

  // Очистка пустых значений (бережно):
  //  - удаляем '' и null для НЕ required полей
  //  - НЕ удаляем пустые массивы (это важно для очистки M2M)
  cleanEmptyValues(obj) {
    const cleaned = { ...obj };
    const required = new Set(this.editor.schema.required || []);

    Object.keys(cleaned).forEach(key => {
      const value = cleaned[key];

      if (value === '' && !required.has(key)) {
        delete cleaned[key];
        return;
      }
      if (value === null && !required.has(key)) {
        delete cleaned[key];
        return;
      }
      // Пустые массивы оставляем — это сигнал "очистить" для M2M
    });

    return cleaned;
  }
}

// # The End
