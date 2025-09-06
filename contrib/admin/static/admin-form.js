// admin-form.js
/** Inline Admin: see contrib/admin/docs/INLINES.md */

// API endpoints injected via templates (see contrib/admin/core/settings)
const { schema: API_SCHEMA } = window.ADMIN_API;

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
        show_errors: 'interaction',
        form_name_root: '\u200B',
        display_required_only: false,
        disable_edit_json: true,
        disable_collapse: true,
        required_by_default: false,
        disable_properties: true,
      },
      endpoints: {
        schema: (a, m, mode, pk) => `${API_SCHEMA}?app=${a}&model=${m}&mode=${mode}` + (pk ? `&pk=${pk}` : ''),
        save: (base, pk) => (pk ? `${base}/${pk}` : base),
        inlines: (base, pk) => `${base}/${pk}/_inlines`,
      },
      debug: false,
    }, config);

    this.inlineLists = this.inlineLists || {};
    this.inlineToggles = {};
    this.inlineBadges = {};
    this.inlineLoadPromises = {};
    this.inlineLoadResolvers = {};
    this._inlinesEventsBound = false;
  }

  bindInlineListEvents() {
    if (this._inlinesEventsBound) return;
    this._inlinesEventsBound = true;

    document.addEventListener('admin:list:changed', (e) => {
      const detail = e && e.detail ? e.detail : {};
      const { app, model, total } = detail;
      if (!app || !model || typeof total !== 'number') return;

      const key = `${app}.${model}`;
      const badge = this.inlineBadges && this.inlineBadges[key];
      if (badge) {
        badge.textContent = String(total);
      }
    });
  }

  parseUrlParams() {
    const usp = new URLSearchParams(window.location.search);
    const presets = {};
    let next = null;
    usp.forEach((value, key) => {
      if (key.startsWith('preset.')) {
        presets[key.slice(7)] = value;
      } else if (key === 'next') {
        next = value;
      }
    });
    return { presets, next };
  }

  applyPresetsToSchemaAndStartval(schema, sv, presets) {
    const schema2 = JSON.parse(JSON.stringify(schema));
    const sv2 = { ...sv };
    Object.entries(presets).forEach(([field, value]) => {
      sv2[field] = value === 'null' ? null : value;
      const prop = schema2?.properties?.[field];
      if (prop) {
        prop.readonly = true;
      }
    });
    return { schema: schema2, startval: sv2 };
  }

  async load() {
    try {
      const { schema, startval } = await this.fetchSchema();

      let sv = startval;
      if (sv === null || typeof sv !== 'object') {
        sv = {};
      }

      const { presets, next } = this.parseUrlParams();
      this.nextUrl = next || null;
      this._presets = Object.keys(presets).length ? presets : null;
      const { schema: schema2, startval: sv2 } = this.applyPresetsToSchemaAndStartval(schema, sv, presets);

      this.spinner.style.display = 'none';

      if (window.FilePathUploader) {
        window.FilePathUploader.init(schema2);
      }

      this.editor = new JSONEditor(this.root, {
        schema: schema2,
        startval: sv2,
        ...this.cfg.defaults,
        display_required_only: false,
      });

      window._editor = this.editor;

      this.hideRootHeader();
      this.bindSubmit();
      this.bindTextareaAutoResize();
      if (this.mode === 'edit' && this.pk) this.loadInlines();

    } catch (err) {
      console.error(err);
      const msg = err?.message ? `Failed to load form: ${err.message}` : 'Failed to load form.';
      alert(msg);
    }
  }

  async fetchSchema() {
    const url = this.cfg.endpoints.schema(this.app, this.model, this.mode, this.pk);
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) {
      let detail = '';
      try {
        const data = await res.json();
        detail = data?.detail || JSON.stringify(data);
      } catch {
        detail = await res.text();
      }
      throw new Error(detail || `Request failed with status ${res.status}`);
    }
    const { schema, startval } = await res.json();
    return { schema, startval };
  }

  async loadInlines() {
    const host = document.getElementById('inline-root');
    if (!host) return;
    try {
      const url = this.cfg.endpoints.inlines(this.base, this.pk);
      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) throw new Error(await res.text());
      const list = await res.json();
      this.renderInlines(list);
    } catch (err) {
      console.error(err);
      host.hidden = true;
    }
  }

  renderInlines(list) {
    const host = document.getElementById('inline-root');
    if (!host) return;
    if (!Array.isArray(list) || list.length === 0) {
      host.hidden = true;
      host.innerHTML = '';
      return;
    }
    host.innerHTML = '';
    list.forEach(item => {
      const key = `${item.app}.${item.model}`;
      const card = document.createElement('div');
      card.className = 'card mb-2';

      const body = document.createElement('div');
      body.className = 'card-body d-flex justify-content-between align-items-center';

      const titleWrap = document.createElement('div');
      titleWrap.className = 'h6 m-0';
      titleWrap.textContent = item.label || '';
      if (item.count !== undefined) {
        const badge = document.createElement('span');
        badge.className = 'badge bg-primary ms-2';
        badge.textContent = String(item.count);
        titleWrap.appendChild(badge);
        this.inlineBadges[key] = badge;
      }

      const btns = document.createElement('div');
      if (item.can_add) {
        const addLink = document.createElement('a');
        addLink.className = 'btn btn-sm btn-outline-primary me-2';
        addLink.textContent = 'Add';
        addLink.href = this.buildAddUrl(item);
        btns.appendChild(addLink);
      }
      const toggleBtn = document.createElement('button');
      toggleBtn.type = 'button';
      toggleBtn.className = 'btn btn-sm btn-outline-secondary me-2';
      const collapsed = item.collapsed !== false;
      toggleBtn.textContent = collapsed ? 'Show' : 'Hide';
      btns.appendChild(toggleBtn);
      this.inlineToggles[key] = toggleBtn;

      const refreshBtn = document.createElement('button');
      refreshBtn.type = 'button';
      refreshBtn.className = 'btn btn-sm btn-outline-secondary me-2';
      refreshBtn.textContent = 'Refresh';
      refreshBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        let inst = this.inlineLists[key];

        if (!inst) {
          toggleBtn.click();
          inst = await this.inlineLoadPromises[key];
        }

        if (mount.hidden) {
          mount.hidden = false;
          toggleBtn.textContent = 'Hide';
        }

        await inst.reload();
      });
      btns.appendChild(refreshBtn);

      const listLink = document.createElement('a');
      listLink.className = 'btn btn-sm btn-outline-secondary';
      listLink.textContent = 'Open list';
      listLink.href = this.buildListUrl(item);
      btns.appendChild(listLink);

      body.appendChild(titleWrap);
      body.appendChild(btns);
      card.appendChild(body);

      const mount = document.createElement('div');
      mount.className = 'inline-list mt-2';
      mount.hidden = collapsed;
      card.appendChild(mount);

      host.appendChild(card);
      this.inlineLoadPromises[key] = new Promise(resolve => {
        this.inlineLoadResolvers[key] = resolve;
      });
      this.bindInlineToggle(item, toggleBtn, mount);
      if (!collapsed) {
        toggleBtn.click();
      }
    });
    host.hidden = false;
    this.bindInlineListEvents();
    this.autoOpenInlineFromHash();
  }

  async ensureAdminList() {
    const root = this.prefix.replace(/\/(orm|settings)$/i, '');
    if (window.AdminList) {
      return `${root}/static/admin-list.js`;
    }
    if (!this._adminListPromise) {
      const url = `${root}/static/admin-list.js`;
      this._adminListPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = url;
        script.onload = () => {
          if (!window.AdminList && typeof AdminList !== 'undefined') {
            window.AdminList = AdminList;
          }
          resolve(url);
        };
        script.onerror = () => {
          const msg = 'Failed to load admin-list.js';
          if (this.showBanner) this.showBanner(msg, 'warning'); else alert(msg);
          reject(new Error(msg));
        };
        document.head.appendChild(script);
      });
    }
    return this._adminListPromise;
  }

  bindInlineToggle(item, btn, mount) {
    const key = `${item.app}.${item.model}`;
    btn.addEventListener('click', async e => {
      e.preventDefault();
      let inst = this.inlineLists[key];
      if (!inst) {
        try {
          await this.ensureAdminList();
          if (!window.AdminList) {
            throw new Error('AdminList is unavailable');
          }
          const fixedParams = {};
          fixedParams[`filter.${item.parent_fk}.eq`] = this.pk;
          if (!mount.id) {
            mount.id = `inline-list-${item.app}-${item.model}`;
          }
          const addUrl = item.can_add ? this.buildAddUrl(item) : null;
          inst = new AdminList({
            embedded: true,
            fixedParams,
            mount,
            app: item.app,
            model: item.model,
            base: `${this.prefix}/${item.app}/${item.model}`,
            returnUrl: location.href,
            allowDelete: item.can_delete === undefined ? true : !!item.can_delete,
            addUrl
          });
          this.inlineLists[key] = inst;
          await inst.load();
          this.inlineLoadResolvers[key]?.(inst);
          mount.hidden = false;
          btn.textContent = 'Hide';
        } catch (err) {
          console.error(err);
          const msg = err?.message ? `Failed to load list: ${err.message}` : 'Failed to load list.';
          if (this.showBanner) this.showBanner(msg, 'warning'); else alert(msg);
          this.inlineLoadResolvers[key]?.(null);
        }
        return;
      }
      mount.hidden = !mount.hidden;
      btn.textContent = mount.hidden ? 'Show' : 'Hide';
      if (!mount.hidden) {
        inst.reload();
      }
    });
  }

  buildAddUrl(item) {
    const back = `${location.href.split('#')[0]}#inline=${item.app}.${item.model}`;
    return `${this.prefix}/${item.app}/${item.model}/add?preset.${item.parent_fk}=${encodeURIComponent(this.pk)}&next=${encodeURIComponent(back)}`;
  }

  buildListUrl(item) {
    return `${this.prefix}/${item.app}/${item.model}/?filter.${item.parent_fk}.eq=${encodeURIComponent(this.pk)}`;
  }

  autoOpenInlineFromHash() {
    const h = location.hash || '';
    const m = h.match(/#inline=([a-z0-9_.-]+)/i);
    if (!m) return;
    const key = m[1];
    const btn = this.inlineToggles && this.inlineToggles[key];
    if (!btn) return;

    // Если ещё не раскрыт — кликнем для ленивого mount
    if (btn.textContent === 'Show') btn.click();

    // Подсветка и прокрутка
    const card = btn.closest('.card');
    if (card) {
      card.classList.add('border', 'border-primary');
      setTimeout(() => card.classList.remove('border', 'border-primary'), 1200);
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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

    // Selective highlight reset: when typing into a field with an error, remove it from external errors
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

  validateWritable() {
    const errs = this.editor.validate();
    return errs.filter(err => {
      const ed = this.editor.getEditor(err.path);
      const schema = ed && ed.schema ? ed.schema : null;
      const ro = schema?.readonly === true || schema?.readOnly === true ||
        schema?.options?.readonly === true || schema?.options?.readOnly === true;
      return !ro;
    });
  }

  bindSubmit() {
    const btn = document.getElementById('submit');
    btn?.addEventListener('click', () => this.onSubmit());
  }

  bindTextareaAutoResize() {
    const resize = (ta) => {
      if (!ta) return;
      const style = window.getComputedStyle(ta);
      const lineHeight = parseFloat(style.lineHeight) || 16;
      const maxHeight = lineHeight * 10;
      ta.style.height = 'auto';
      const newHeight = Math.min(ta.scrollHeight, maxHeight);
      ta.style.height = `${newHeight}px`;
      ta.style.overflowY = ta.scrollHeight > maxHeight ? 'auto' : 'hidden';
    };

    this.root.querySelectorAll('textarea').forEach(resize);
    this.root.addEventListener('input', (e) => {
      const ta = e.target;
      if (ta && ta.tagName === 'TEXTAREA') {
        resize(ta);
      }
    });
  }

  async onSubmit() {
    const btn = document.getElementById('submit');
    btn?.setAttribute('disabled', 'disabled');
    this.editor.showValidationErrors([]);
    this._extErrors = [];
    this.showBanner('');

    const errs = this.validateWritable();
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
      const headers = { 'Content-Type': 'application/json' };
      if (!this.pk && this._presets) {
        Object.entries(this._presets).forEach(([field, value]) => {
          headers['X-Force-FK-' + field] = String(value ?? '');
        });
      }
      const resp = await fetch(url, {
        method,
        headers,
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
      if (this.nextUrl) {
        window.location.href = this.nextUrl;
      } else {
        window.location.href = `${this.base}/`;
      }
    } catch (err) {
      console.error(err);
      alert('Network error during save.');
      btn?.removeAttribute('disabled');
    }
  }

  _collectRequired(schema, prefix = '') {
    const required = new Set();
    if (!schema || typeof schema !== 'object') return required;
    const own = Array.isArray(schema.required) ? schema.required : [];
    own.forEach(key => required.add(prefix ? `${prefix}.${key}` : key));
    const props = schema.properties || {};
    Object.entries(props).forEach(([key, sub]) => {
      const subPrefix = prefix ? `${prefix}.${key}` : key;
      this._collectRequired(sub, subPrefix).forEach(p => required.add(p));
    });
    return required;
  }

  // Cleaning empty values (carefully):
  //  - remove '' and null for non-required fields
  //  - do NOT remove empty arrays (important for clearing M2M)
  cleanEmptyValues(obj) {
    const required = this._collectRequired(this.editor.schema);
    const prune = (value, path = '') => {
      if (Array.isArray(value)) {
        return value.map(item => prune(item, path));
      }
      if (value && typeof value === 'object') {
        const result = {};
        Object.keys(value).forEach(key => {
          const full = path ? `${path}.${key}` : key;
          const v = prune(value[key], full);
          if (v === '' && !required.has(full)) return;
          if (v === null && !required.has(full)) return;
          result[key] = v;
        });
        return result;
      }
      return value;
    };
    return prune(obj);
  }
}

// # The End

