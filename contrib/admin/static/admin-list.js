/** Inline Admin: see contrib/admin/docs/INLINES.md */

class ActionModal {
  constructor() {
    this.el = document.getElementById('actionModal');
    this.modal = this.el ? new bootstrap.Modal(this.el) : null;
    this.form = document.getElementById('action-form');
    this.title = document.getElementById('action-title');
    this.fields = document.getElementById('action-fields');
    this.errors = document.getElementById('action-errors');
    this.callback = null;
    this.form?.addEventListener('submit', e => {
      e.preventDefault();
      this.submit();
    });
  }

  open(spec, cb) {
    this.callback = cb;
    if (!this.modal) { this.callback({}); return; }
    this.title.textContent = spec.label || spec.name;
    this.buildFields(spec.params_schema || {});
    this.errors.textContent = '';
    this.modal.show();
  }

  buildFields(schema) {
    this.fields.innerHTML = '';
    for (const [key, type] of Object.entries(schema)) {
      const wrap = document.createElement('div');
      if (type === 'boolean') {
        wrap.className = 'form-check';
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.id = `param-${key}`;
        input.className = 'form-check-input';
        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.htmlFor = input.id;
        label.textContent = key.replace(/_/g, ' ');
        wrap.appendChild(input);
        wrap.appendChild(label);
      } else {
        wrap.className = 'mb-3';
        const label = document.createElement('label');
        label.className = 'form-label';
        label.htmlFor = `param-${key}`;
        label.textContent = key.replace(/_/g, ' ');
        const input = document.createElement('input');
        input.type = (type === 'number' || type === 'integer') ? 'number' : 'text';
        input.id = `param-${key}`;
        input.className = 'form-control';
        wrap.appendChild(label);
        wrap.appendChild(input);
      }
      this.fields.appendChild(wrap);
    }
  }

  collect() {
    const params = {};
    this.fields.querySelectorAll('input').forEach(inp => {
      const key = inp.id.replace(/^param-/, '');
      let value = inp.type === 'checkbox'
        ? inp.checked
        : (inp.type === 'number' ? (inp.value === '' ? null : Number(inp.value)) : inp.value);
      if (value !== null && value !== '') {
        params[key] = value;
      }
    });
    return params;
  }

  submit() {
    if (this.callback) {
      const params = this.collect();
      this.modal?.hide();
      this.callback(params);
    }
  }
}

class AdminList {
  static OPS = ['eq','icontains','gte','lte','gt','lt','in'];
  static FILTER_PREFIX = 'filter.';
  constructor(config = {}) {
    const cfg = typeof config === 'object' && config !== null ? config : {};
    this.uid = cfg.uid || `al-${Math.random().toString(36).slice(2)}`;
    this.scope = document;
    this.embedded = cfg.embedded ?? false;
    this.fixedParams = cfg.fixedParams ?? {};
    this.app = cfg.app ?? null;
    this.model = cfg.model ?? null;
    this.mount = cfg.mount ?? null;
    this.returnUrl = cfg.returnUrl ?? null;
    this.allowDelete = cfg.allowDelete ?? true;
    this.addUrl = cfg.addUrl ?? null;
    this.total = 0;

    if (this.embedded && this.mount) this.buildEmbeddedSkeleton();

    const path = (cfg.base ? cfg.base : window.location.pathname).replace(/\/$/, '');
    this.base = path;
    // explicit list API endpoint
    this.api = cfg.api || `${path}/_list`;

    const usp = new URLSearchParams(window.location.search);
    const order = usp.get('order') ?? '';

    this.state = { search: '', page: 1, per_page: 20, order, id_field: 'id' };

    this.input = this.el('search');
    this.btn = this.el('btn-search');
    this.perPage = this.el('per-page');
    this.rangeInfo = this.el('range-info');
    this.thead = this.el('thead-row');
    this.selectAll = this.el('select-all');
    this.selectedIds = new Set();
    this.tbody = this.el('tbody');
    this.table = this.el('list-table');
    this.pager = this.el('pager');
    this.spinner = this.el('list-spinner');
    this.empty = this.el('empty-state');
    this.clearFiltersBtn = this.el('clear-filters-btn');
    this.filterChips = this.el('active-filters');
    this.filtersCount = this.el('filters-count');
    this.filtersBtn = this.el('btn-filters');
    this.deleteId = null;
    this.actionsWrap = this.el('actions-wrapper');
    this.actionSelect = this.el('action-select');
    this.actionApply = this.el('action-apply');
    this.hasActions = false;
    this.actions = {};
    this.actionModal = new ActionModal();

    this.initDeleteModal();

    if (this.embedded) {
      this.input?.closest('.input-group')?.classList.add('d-none');
      this.filtersBtn?.classList.add('d-none');
      this.actionsWrap?.classList.add('d-none');
      this.filterChips?.classList.add('d-none');
      this.clearFiltersBtn?.classList.add('d-none');
      this.rangeInfo?.classList.add('d-none');
      this.perPage?.closest('div')?.classList.add('d-none');
      this.selectAll?.closest('th')?.classList.add('d-none');
    }

    this.btn?.addEventListener('click', () => this.doSearch());
    this.input?.addEventListener('keydown', e => { if (e.key === 'Enter') this.doSearch(); });
    this.input?.addEventListener('input', this.debounce(() => this.doSearch(), 300));
    this.perPage?.addEventListener('change', () => { this.state.per_page = parseInt(this.perPage.value); this.state.page = 1; this.load(); });
    this.clearFiltersBtn?.addEventListener('click', () => this.clearFilters());
    this.actionApply?.addEventListener('click', () => this.runAction());
    this.selectAll?.addEventListener('change', e => {
      this.toggleAll(e.target.checked);
      this.updateActionVisibility();
    });
    this.renderFilterChips();
    this.loadActions();
  }

  el(id){
    return this.scope.querySelector(`#${id}`) || this.scope.querySelector(`#${this.uid}-${id}`);
  }

  buildEmbeddedSkeleton(){
    let root = this.mount;
    if (typeof root === 'string') root = document.getElementById(root);
    if (!root) return;
    this.scope = root;
    root.innerHTML = '';
    root.innerHTML = `
      <div id="${this.uid}-list-spinner" class="spinner-border" role="status" style="display:none;">
        <span class="visually-hidden">Loading...</span>
      </div>
      <div id="${this.uid}-empty-state" class="alert alert-secondary d-none"></div>
      <div class="table-responsive">
        <table id="${this.uid}-list-table" class="table">
          <thead><tr id="${this.uid}-thead-row"><th><input type="checkbox" id="${this.uid}-select-all"></th></tr></thead>
          <tbody id="${this.uid}-tbody"></tbody>
        </table>
      </div>
      <nav id="${this.uid}-pager"></nav>
    `;
  }

  initDeleteModal(){
    let modalEl = document.getElementById('deleteModal');
    let confirmBtn = document.getElementById('confirm-delete');
    let objSpan = document.getElementById('del-obj');
    if ((!modalEl || !confirmBtn || !objSpan) && this.embedded && this.mount){
      let root = this.mount;
      if (typeof root === 'string') root = document.getElementById(root);
      if (root){
        root.insertAdjacentHTML('afterend', `
      <div class="modal fade" id="${this.uid}-deleteModal" tabindex="-1">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Delete item</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">Are you sure you want to delete this item <span id="${this.uid}-del-obj"></span>?</div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
              <button type="button" class="btn btn-danger" id="${this.uid}-confirm-delete">Delete</button>
            </div>
          </div>
        </div>
      </div>`);
        modalEl = document.getElementById(`${this.uid}-deleteModal`);
        confirmBtn = document.getElementById(`${this.uid}-confirm-delete`);
        objSpan = document.getElementById(`${this.uid}-del-obj`);
      }
    }
    this.deleteModal = modalEl ? new bootstrap.Modal(modalEl) : null;
    this.confirmDelete = confirmBtn;
    this.delObj = objSpan;
    this.confirmDelete?.addEventListener('click', () => this.onConfirmDelete());
  }

  onSort(key){
    const current = this.state.order || '';
    const isThis = current.replace(/^-/, '') === key;
    const next = !isThis ? key : (current.startsWith('-') ? key : `-${key}`);
    this.state.order = next;
    this.state.page = 1;
    if (!this.embedded) {
      const url = new URL(window.location);
      url.searchParams.set('order', next);
      url.searchParams.delete('page_num');
      this.mergeFixedParams(url.searchParams);
      history.replaceState(null, '', url);
    }
    this.load();
  }

  qs(params){
    const usp = new URLSearchParams();
    for(const [k,v] of Object.entries(params)) if(v!=='' && v!=null) usp.set(k, v);
    this.mergeFixedParams(usp);
    return usp.toString();
  }

  mergeFixedParams(sp){
    for(const [k,v] of Object.entries(this.fixedParams)) if(!sp.has(k)) sp.set(k, v);
  }

  debounce(fn, delay){
    let t; return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn.apply(this,args), delay); };
  }

  doSearch(){
    this.state.search = this.input?.value.trim() ?? '';
    this.state.page = 1;
    this.load();
  }

  renderFilterChips(){
    if (!this.filterChips) return;
    this.filterChips.innerHTML = '';
    const usp = new URLSearchParams(window.location.search);
    const prefix = AdminList.FILTER_PREFIX;
    const groups = new Map();
    for (const [k, v] of usp.entries()) {
      if (!k.startsWith(prefix)) continue;
      const parts = k.slice(prefix.length).split('.');
      const last = parts[parts.length - 1];
      const fieldParts = AdminList.OPS.includes(last) ? parts.slice(0, -1) : parts;
      const fieldKey = fieldParts.join('.');
      const entry = groups.get(fieldKey) || [];
      entry.push({ key: k, value: v, label: fieldParts.join('.').replace(/_/g, ' ') });
      groups.set(fieldKey, entry);
    }
    for (const entries of groups.values()) {
      const badge = document.createElement('span');
      badge.className = 'badge bg-secondary';
      const lbl = entries[0].label;
      const vals = entries.map(e => e.value).join(', ');
      badge.textContent = `${lbl}: ${vals} `;
      const close = document.createElement('span');
      close.style.cursor = 'pointer';
      close.innerHTML = '&times;';
      close.addEventListener('click', () => {
        const url = new URL(location.href);
        for (const e of entries) url.searchParams.delete(e.key);
        url.searchParams.delete('page_num');
        this.mergeFixedParams(url.searchParams);
        location.href = url.toString();
      });
      badge.appendChild(close);
      this.filterChips.appendChild(badge);
    }
    const count = groups.size;
    this.filterChips.classList.toggle('d-none', count === 0);
    if (this.filtersCount) {
      this.filtersCount.textContent = count;
      this.filtersCount.hidden = count === 0;
    }
  }

  async load(isRetry = false){
    this._isLoading = true;
    if (!isRetry) this._pageCorrected = false;
    this.spinner.style.display = '';
    this.empty.classList.add('d-none');
    const pageQS = new URLSearchParams(window.location.search);
    const baseParams = { search: this.state.search, page_num: this.state.page, per_page: this.state.per_page, order: this.state.order };
    const usp = new URLSearchParams();
    for (const [k, v] of Object.entries(baseParams)) if (v !== '' && v != null) usp.set(k, v);
    const prefix = AdminList.FILTER_PREFIX;
    if (!this.embedded) {
      for (const k of Array.from(pageQS.keys())) {
        if (k.startsWith(prefix)) usp.set(k, pageQS.get(k));
      }
    }
    this.mergeFixedParams(usp);
    const url = `${this.api}?${usp.toString()}`;
    try {
      const res = await fetch(url, {credentials:'same-origin'});
      if(!res.ok){ console.log(await res.text()); return; }
      const data = await res.json();
      if (!this._pageCorrected &&
          this.state.page > 1 &&
          Array.isArray(data.items) && data.items.length === 0 &&
          Number(data.total || 0) > 0) {
        this._pageCorrected = true;
        this.state.page = this.state.page - 1;
        await this.load(true);
        return;
      }
      this.render(data);
      this.total = Number(data?.total ?? 0);
      this.emitChanged();
    } catch(err) {
      console.log('Error loading list:', err);
      alert('Failed to load data');
    } finally {
      this.spinner.style.display = 'none';
      this._isLoading = false;
    }
  }

  emitChanged(){
    document.dispatchEvent(new CustomEvent('admin:list:changed', {
      detail: { app: this.app, model: this.model, total: this.total }
    }));
  }

  async reload(){
    await this.load();
  }

  clearFilters(){
    window._filters?.reset?.();
    const url = new URL(location.href);
    const prefix = AdminList.FILTER_PREFIX;
    for (const k of Array.from(url.searchParams.keys())) {
      if (k.startsWith(prefix)) url.searchParams.delete(k);
    }
    url.searchParams.delete('page_num');
    this.mergeFixedParams(url.searchParams);
    location.href = url.toString();
  }

  fmtCell(val, meta){
    if(val==null) return '';
    switch(meta?.type){
      case 'boolean':
        return val ? '✓' : '✗';
      case 'choice':
        return meta?.choices_map?.[String(val)] ?? '—';
      case 'datetime': {
        const d = new Date(val);
        return isNaN(d.getTime()) ? '—' : d.toLocaleString(undefined, { timeZoneName: 'short' });
      }
      default:
        return typeof val === 'object' ? JSON.stringify(val) : String(val);
    }
  }

  render({columns, columns_meta, items, page, pages, total, order, per_page, id_field}){
    this.state.page = page;
    this.state.order = order;
    this.state.per_page = per_page;
    this.state.id_field = id_field;
    if (this.perPage) this.perPage.value = String(per_page);
    this.selectedIds.clear();

    // header
    while(this.thead.children.length > 1) this.thead.removeChild(this.thead.lastChild);
    const thSel = this.thead.children[0];
    if(this.embedded){
      thSel.classList.add('d-none');
    }else{
      thSel.style.width = '1%';
      thSel.style.whiteSpace = 'nowrap';
      if (this.selectAll) this.selectAll.checked = false;
    }
    const metaMap = Object.fromEntries(columns_meta.map(m=>[m.key, m]));
    columns.forEach((col, idx)=>{
      const meta = metaMap[col] || {};
      const th = document.createElement('th');
      th.textContent = meta.label || col;
      if(meta.sortable){
        th.style.cursor = 'pointer';
        th.addEventListener('click', ()=>this.onSort(meta.key));
      }
      const ordField = (order||'').replace(/^-/, '');
      if(ordField === meta.key){
        const up = !order.startsWith('-');
        th.insertAdjacentHTML('beforeend', up ? ' ▲' : ' ▼');
      }
      if(idx === 0){
        th.style.whiteSpace = 'nowrap';
      }
      this.thead.appendChild(th);
    });
    const thAct = document.createElement('th');
    thAct.className = 'text-end';
    thAct.style.width = '1%';
    thAct.style.whiteSpace = 'nowrap';
    thAct.textContent = 'Actions';
    this.thead.appendChild(thAct);

    // body
    this.tbody.innerHTML = '';
    if (items.length === 0) {
      this.table.classList.add('d-none');
      this.empty.textContent = 'No items';
      if (this.addUrl !== null) {
        const btn = document.createElement('a');
        btn.className = 'btn btn-sm btn-primary ms-2';
        btn.textContent = 'Add first';
        btn.href = this.addUrl;
        this.empty.appendChild(btn);
      }
      this.empty.classList.remove('d-none');
    } else {
      this.empty.classList.add('d-none');
      this.empty.textContent = '';
      this.table.classList.remove('d-none');
    }
    items.forEach(row=>{
      const tr = document.createElement('tr');
      const id = row[this.state.id_field] ?? row.id ?? row.pk ?? row.ID;
      if(row.can_change){
        tr.style.cursor = 'pointer';
        const editUrl = `${this.base}/${id}/edit` + (this.embedded && this.returnUrl ? `?next=${encodeURIComponent(this.returnUrl)}` : '');
        tr.addEventListener('click', ()=>{ if(id!=null) window.location.href = editUrl; });
      } else {
        tr.style.cursor = 'default';
      }
      if(!this.embedded){
        const tdSel = document.createElement('td');
        tdSel.className = 'text-center';
        tdSel.style.width = '1%';
        tdSel.style.whiteSpace = 'nowrap';
        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.className = 'row-select';
        chk.dataset.id = id;
        chk.checked = this.selectedIds.has(String(id));
        chk.addEventListener('click', e=>e.stopPropagation());
        chk.addEventListener('change', e=>this.onRowSelect(id, e.target.checked));
        tdSel.appendChild(chk);
        tr.appendChild(tdSel);
      }
      columns.forEach((col, idx)=>{
        const meta = metaMap[col] || {};
        const td = document.createElement('td');
        td.textContent = this.fmtCell(row[col], meta);
        if(idx === 0) td.style.whiteSpace = 'nowrap';
        tr.appendChild(td);
      });
      const tdAct = document.createElement('td');
      tdAct.className = 'text-end';
      tdAct.style.whiteSpace = 'nowrap';
      const editUrl = `${this.base}/${id}/edit` + (this.embedded && this.returnUrl ? `?next=${encodeURIComponent(this.returnUrl)}` : '');
      if(row.can_change){
        const editLink = document.createElement('a');
        editLink.className = 'btn btn-sm btn-outline-primary me-2';
        editLink.innerHTML = '<i class="bi bi-pencil"></i>';
        editLink.href = editUrl;
        editLink.addEventListener('click', e=>e.stopPropagation());
        tdAct.appendChild(editLink);
      }
      if(this.allowDelete !== false && row.can_delete){
        const delBtn = document.createElement('button');
        delBtn.className = 'btn btn-sm btn-danger';
        delBtn.innerHTML = '<i class="bi bi-trash"></i>';
        delBtn.setAttribute('aria-label', 'Delete');
        delBtn.addEventListener('click', e=>{ e.stopPropagation(); this.showDeleteModal(id, row.row_str ?? id); });
        tdAct.appendChild(delBtn);
      }
      tr.appendChild(tdAct);
      this.tbody.appendChild(tr);
    });
    this.updateSelectAllState();

    this.updateActionVisibility();

    // range info
    const start = total ? (page-1)*per_page + 1 : 0;
    const end = total ? (start + items.length - 1) : 0;
    if (this.rangeInfo) this.rangeInfo.textContent = total ? `${start}–${end} of ${total}` : '0 results';

    // pager
    this.renderPager(page, pages);
  }

  onRowSelect(id, checked){
    this.toggleSelection(id, checked);
    this.updateSelectAllState();
    this.updateActionVisibility();
  }

  toggleSelection(id, checked){
    if(id==null) return;
    const key = String(id);
    if(checked) this.selectedIds.add(key); else this.selectedIds.delete(key);
  }

  toggleAll(checked){
    if (!this.selectAll) return;
    const boxes = this.tbody.querySelectorAll('input.row-select');
    boxes.forEach(cb=>{
      cb.checked = checked;
      this.toggleSelection(cb.dataset.id, checked);
    });
    this.updateSelectAllState();
  }

  updateSelectAllState(){
    if (!this.selectAll) return;
    const boxes = this.tbody.querySelectorAll('input.row-select');
    const all = boxes.length>0 && Array.from(boxes).every(cb=>cb.checked);
    if (this.selectAll) this.selectAll.checked = all;
  }

  getSelectedIds(){
    return Array.from(this.selectedIds);
  }

  renderPager(page, pages){
    this.pager.innerHTML = '';
    const ul = document.createElement('ul');
    ul.className = 'pagination';
    const mk = (label, p, disabled=false, active=false)=>{
      const li = document.createElement('li');
      li.className = `page-item${disabled?' disabled':''}${active?' active':''}`;
      const a = document.createElement('a');
      a.className = 'page-link';
      const url = new URL(window.location);
      url.searchParams.set('page_num', p);
      this.mergeFixedParams(url.searchParams);
      a.href = url.toString();
      a.textContent = label;
      a.addEventListener('click', e=>{ e.preventDefault(); if(disabled||active) return; this.state.page = p; this.load(); });
      li.appendChild(a);
      return li;
    };
    ul.appendChild(mk('«', 1, page<=1));
    ul.appendChild(mk('‹', Math.max(1,page-1), page<=1));
    const startP = Math.max(1, page-2), endP = Math.min(pages, startP+4);
    for(let p=startP;p<=endP;p++) ul.appendChild(mk(String(p), p, false, p===page));
    ul.appendChild(mk('›', Math.min(pages,page+1), page>=pages));
    ul.appendChild(mk('»', pages, page>=pages));
    this.pager.appendChild(ul);
  }

  showDeleteModal(id, repr){
    this.deleteId = id;
    if(this.delObj) this.delObj.textContent = repr;
    this.deleteModal?.show?.();
  }

  async onConfirmDelete(){
    if(this.deleteId==null) return;
    const url = `${this.base}/${encodeURIComponent(this.deleteId)}`;
    const res = await fetch(url, {method:'DELETE', credentials:'same-origin'});
    if(res.ok){
      this.deleteModal?.hide();
      await this.reload();
    }
    else{ console.log(await res.text()); }
  }

  async loadActions(){
    if(!this.actionSelect) return;
    try{
      const res = await fetch(`${this.base}/_actions`, {credentials:'same-origin'});
      if(!res.ok){ console.log(await res.text()); return; }
      const data = await res.json();
      this.actionSelect.innerHTML = '';
      this.actions = {};
      for(const spec of data){
        this.actions[spec.name] = spec;
        const opt = document.createElement('option');
        opt.value = spec.name;
        opt.textContent = spec.label || spec.name;
        this.actionSelect.appendChild(opt);
      }
      this.hasActions = data.length > 0;
      this.updateActionVisibility();
    }catch(err){
      console.log('Error loading actions:', err);
    }
  }

  updateActionVisibility(){
    if(!this.actionsWrap) return;
    const show = this.hasActions && this.selectedIds.size > 0;
    this.actionsWrap.hidden = !show;
  }

  async runAction(){
    const name = this.actionSelect?.value;
    if(!name || this.selectedIds.size === 0) return;
    const spec = this.actions?.[name] || {};
    const proceed = async params => {
      if(name === 'export_selected_wizard'){
        const ids = this.getSelectedIds();
        try{
          const res = await fetch(`${this.base}/_actions/token`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            credentials:'same-origin',
            body: JSON.stringify({scope:{type:'ids', ids}})
          });
          if(!res.ok) return;
          const data = await res.json();
          const url = new URL(`${this.base}/export/`, window.location.origin);
          if(data.scope_token) url.searchParams.set('scope_token', data.scope_token);
          window.location.href = url.toString();
        }catch(err){
          console.log('Error obtaining scope token', err);
        }
        return;
      }
      this.executeAction(name, params);
    };
    if(spec.params_schema && Object.keys(spec.params_schema).length>0){
      this.actionModal.open(spec, proceed);
    }else{
      await proceed({});
    }
  }

  async executeAction(name, params){
    const url = `${this.base}/_actions/${encodeURIComponent(name)}`;
    try{
      const res = await fetch(url, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body: JSON.stringify({ids: this.getSelectedIds(), params})
      });
      if(!res.ok){ console.log(await res.text()); return; }
      const result = await res.json();
      const msgs = [];
      if(result.report) msgs.push(result.report);
      if(result.errors && result.errors.length) msgs.push(result.errors.join('\n'));
      if(msgs.length) alert(msgs.join('\n'));
      this.selectedIds.clear();
      this.updateActionVisibility();
      await this.reload();
    }catch(err){
      console.log('Error running action:', err);
    }
  }
}

// # The End

