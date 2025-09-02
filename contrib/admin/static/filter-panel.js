// API endpoints injected via templates (see contrib/admin/core/settings)
const { list_filters: API_LIST_FILTERS } = window.ADMIN_API;

function sanitizeId(name) {
  return `filter-${String(name).toLowerCase().replace(/\./g, '__').replace(/[^a-z0-9_-]/gi, '-')}`;
}

class BaseFilter {
  constructor(field, qs) {
    this.field = field;
    this.qs = qs;
    this.prefix = FiltersPanel.PREFIX;
  }

  render() { return document.createElement('div'); }
  apply() {}

  static create(field, qs) {
    const kind = String(field.kind || field.type || '').toLowerCase();
    if (kind === 'bool' || kind === 'boolean') return new BooleanFilter(field, qs);
    if (kind === 'choice') return new ChoiceFilter(field, qs);
    if (['number', 'int', 'integer', 'date', 'datetime'].includes(kind)) return new RangeFilter(field, qs);
    return new TextFilter(field, qs);
  }
}

class TextFilter extends BaseFilter {
  render() {
    const ops = (this.field.ops || []).filter(op => ['eq', 'icontains'].includes(op));
    this.ops = ops.length ? ops : ['eq'];
    const wrap = document.createElement('div');
    wrap.className = 'mb-3';
    const label = document.createElement('label');
    label.className = 'form-label mb-1';
    const id = sanitizeId(this.field.name);
    label.setAttribute('for', id);
    label.textContent = this.field.label;
    wrap.appendChild(label);
    const row = document.createElement('div');
    row.className = 'd-flex gap-2';
    if (this.ops.length > 1) {
      this.opSelect = document.createElement('select');
      this.opSelect.className = 'form-select';
      for (const op of this.ops) {
        const opt = document.createElement('option');
        opt.value = op;
        opt.textContent = op === 'eq' ? 'Equals' : 'Contains';
        this.opSelect.appendChild(opt);
      }
      row.appendChild(this.opSelect);
    }
    this.input = document.createElement('input');
    this.input.type = 'text';
    this.input.className = 'form-control';
    this.input.id = id;
    let selOp = this.ops[0];
    for (const op of this.ops) {
      const val = this.qs.get(`${this.prefix}${this.field.name}.${op}`);
      if (val != null) { selOp = op; this.input.value = val; break; }
    }
    if (this.opSelect) this.opSelect.value = selOp;
    row.appendChild(this.input);
    wrap.appendChild(row);
    return wrap;
  }

  apply(sp) {
    const val = this.input.value.trim();
    if (!val) return;
    const op = this.opSelect ? this.opSelect.value : this.ops[0];
    sp.set(`${this.prefix}${this.field.name}.${op}`, val);
  }
}

class ChoiceFilter extends BaseFilter {
  render() {
    const wrap = document.createElement('div');
    wrap.className = 'mb-3';
    const label = document.createElement('label');
    label.className = 'form-label mb-1';
    const id = sanitizeId(this.field.name);
    label.setAttribute('for', id);
    label.textContent = this.field.label;
    wrap.appendChild(label);
    this.select = document.createElement('select');
    this.select.className = 'form-select';
    this.select.id = id;
    this.hasIn = (this.field.ops || []).includes('in');
    if (!this.hasIn) {
      const any = document.createElement('option');
      any.value = '';
      any.textContent = 'Any';
      this.select.appendChild(any);
    } else {
      this.select.multiple = true;
    }
    for (const ch of this.field.choices || []) {
      const opt = document.createElement('option');
      opt.value = ch.value;
      opt.textContent = ch.label;
      this.select.appendChild(opt);
    }
    const base = `${this.prefix}${this.field.name}.`;
    const inVal = this.qs.get(`${base}in`);
    const eqVal = this.qs.get(`${base}eq`);
    if (this.hasIn && inVal) {
      const vals = inVal.split(',');
      for (const opt of this.select.options) if (vals.includes(opt.value)) opt.selected = true;
    } else if (this.hasIn && eqVal) {
      for (const opt of this.select.options) if (opt.value === eqVal) opt.selected = true;
    } else if (eqVal) {
      this.select.value = eqVal;
    }
    wrap.appendChild(this.select);
    return wrap;
  }

  apply(sp) {
    const vals = Array.from(this.select.selectedOptions).map(o => o.value).filter(v => v !== '');
    if (!vals.length) return;
    const op = this.hasIn ? 'in' : 'eq';
    sp.set(`${this.prefix}${this.field.name}.${op}`, this.hasIn ? vals.join(',') : vals[0]);
  }
}

class BooleanFilter extends BaseFilter {
  render() {
    const wrap = document.createElement('div');
    wrap.className = 'mb-3';
    const label = document.createElement('label');
    label.className = 'form-label mb-1';
    const id = sanitizeId(this.field.name);
    label.setAttribute('for', id);
    label.textContent = this.field.label;
    wrap.appendChild(label);
    this.select = document.createElement('select');
    this.select.className = 'form-select';
    this.select.id = id;
    this.select.innerHTML = `
          <option value="">Any</option>
          <option value="true">Yes</option>
          <option value="false">No</option>`;
    const val = this.qs.get(`${this.prefix}${this.field.name}.eq`);
    if (val != null) this.select.value = val;
    wrap.appendChild(this.select);
    return wrap;
  }

  apply(sp) {
    const val = this.select.value;
    if (val !== '') sp.set(`${this.prefix}${this.field.name}.eq`, val);
  }
}

class RangeFilter extends BaseFilter {
  getInputType() {
    const kind = String(this.field.kind || '').toLowerCase();
    if (['int', 'integer', 'number'].includes(kind)) return 'number';
    if (kind === 'date') return 'date';
    if (kind === 'datetime') return 'datetime-local';
    return 'text';
  }

  render() {
    const wrap = document.createElement('div');
    wrap.className = 'mb-3';
    const label = document.createElement('label');
    label.className = 'form-label mb-1';
    const id = sanitizeId(this.field.name);
    label.setAttribute('for', id);
    label.textContent = this.field.label;
    wrap.appendChild(label);
    const row = document.createElement('div');
    row.className = 'd-flex gap-2';
    const type = this.getInputType();
    if ((this.field.ops || []).includes('gte')) {
      this.from = document.createElement('input');
      this.from.type = type;
      this.from.className = 'form-control';
      this.from.id = id;
      const val = this.qs.get(`${this.prefix}${this.field.name}.gte`);
      if (val != null) this.from.value = val;
      row.appendChild(this.from);
    }
    if ((this.field.ops || []).includes('lte')) {
      this.to = document.createElement('input');
      this.to.type = type;
      this.to.className = 'form-control';
      const val2 = this.qs.get(`${this.prefix}${this.field.name}.lte`);
      if (val2 != null) this.to.value = val2;
      row.appendChild(this.to);
    }
    wrap.appendChild(row);
    return wrap;
  }

  apply(sp) {
    if (this.from && this.from.value !== '') sp.set(`${this.prefix}${this.field.name}.gte`, this.from.value);
    if (this.to && this.to.value !== '') sp.set(`${this.prefix}${this.field.name}.lte`, this.to.value);
  }
}

class FiltersPanel {
  static PREFIX = 'filter.';
  constructor({ offcanvasId = 'filtersOffcanvas', formId = 'filters-form', buttonId = 'btn-filters', clearButtonId = 'clear-filters-btn', app = '', model = '' } = {}) {
    this.el = document.getElementById(offcanvasId);
    this.form = document.getElementById(formId);
    this.button = document.getElementById(buttonId);
    this.clearButton = document.getElementById(clearButtonId);
    this.canvas = (this.el && window.bootstrap) ? new bootstrap.Offcanvas(this.el, { backdrop: true }) : null;
    this.qs = new URLSearchParams(location.search);

    if (this.form) {
      this.form.addEventListener('submit', (e) => { e.preventDefault(); this.apply(); });
    }

    // `API_LIST_FILTERS` already contains the full base path, so no extra
    // prefix should be prepended here.
    this.filters = [];
    this.load(app, model);
  }

  async load(app, model) {
    if (!app || !model) {
      this.button?.setAttribute('hidden', '');
      this.clearButton?.setAttribute('hidden', '');
      return;
    }
    try {
      const res = await fetch(`${API_LIST_FILTERS}?app=${app}&model=${model}`, {
        credentials: 'same-origin',
      });
      const data = await res.json();
      const specs = data.filters || [];
      if (!specs.length) {
        this.button?.setAttribute('hidden', '');
        this.clearButton?.setAttribute('hidden', '');
        return;
      }
      this.render(specs);
      this.button?.removeAttribute('hidden');
      this.clearButton?.removeAttribute('hidden');
    } catch (err) {
      this.button?.setAttribute('hidden', '');
      this.clearButton?.setAttribute('hidden', '');
    }
  }

  
  render(specs) {
    const form = this.form;
    if (!form) return;
    form.innerHTML = '';
    this.filters = [];
    for (const sp of specs) {
      try {
        const f = BaseFilter.create(sp, this.qs);
        this.filters.push(f);
        form.appendChild(f.render());
      } catch (err) {
        console.warn('Failed to render filter field', sp, err);
      }
    }
    const btnWrap = document.createElement('div');
    btnWrap.className = 'd-flex gap-2 mt-3';
    btnWrap.innerHTML = `
      <button type="submit" class="btn btn-primary">Apply</button>
      <button type="button" class="btn btn-outline-secondary" data-action="reset">Reset</button>`;
    form.appendChild(btnWrap);
    form.querySelector('[data-action="reset"]').addEventListener('click', () => this.reset());
  }

  apply() {
    const url = new URL(location.href);
    const prefix = FiltersPanel.PREFIX;
    for (const k of Array.from(url.searchParams.keys())) if (k.startsWith(prefix)) url.searchParams.delete(k);
    for (const f of this.filters) f.apply(url.searchParams);
    url.searchParams.delete('page_num');
    location.href = url.toString();
  }

  reset() {
    const url = new URL(location.href);
    const prefix = FiltersPanel.PREFIX;
    for (const k of Array.from(url.searchParams.keys())) if (k.startsWith(prefix)) url.searchParams.delete(k);
    url.searchParams.delete('page_num');
    location.href = url.toString();
  }

  show() { this.canvas?.show(); }
}

// # The End

