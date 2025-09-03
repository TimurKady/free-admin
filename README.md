# Admin panel for FastAPI/Tortoise-ORM

> ⚠️ This project is in an early experimental stage.  
> It is under active development and may change at any time.  
> Nothing is guaranteed to work as expected — use at your own risk.

A modular, Django-Admin–grade admin for **FastAPI** + **Tortoise ORM** without monoliths or client-side “magic”.
Bootstrap 5 UI, JSON-Editor forms, clean layering, two modes (ORM/Settings), strict RBAC, and pluggable widgets.

## ✨ Highlights

* **Clean layering**

  * `AdminSite` (coordinator), `PageRegistry`, `CrudRouterBuilder`, `ApiController`, `TemplateProvider`
  * `ModelAdmin` (domain): JSON-Schema forms, list, filters, validation, QS hooks, RLS, `allow()`
* **Two modes of the same model**

  * **ORM**: `/orm/<app>/<model>/…` with model permissions `view/add/change/delete`
  * **Settings**: `/settings/<app>/<model>/…` with global permissions `view/change`
* **Minimal frontend magic**

  * Bootstrap 5 + JSON-Editor; pre-baked schemas; no live patching
* **Separation & packaging**

  * Core as a pip package; templates/static included; demo app optional
* **Widgets architecture**

  * Field widgets (for JSON-Editor) and free widgets (page cards), unified asset delivery

---

## Contents

* [Quickstart](#quickstart)
* [Architecture](#architecture)
* [Registering admins](#registering-admins)
* [System configuration](#system-configuration)
* [Permissions (RBAC)](#permissions-rbac)
* [Templates & UI](#templates--ui)
* [Filters & query syntax](#filters--query-syntax)
* [Widgets](#widgets)
* [Create superuser CLI](#create-superuser-cli)
* [Roadmap](#roadmap)
* [License](#license)

---

## Quickstart

```bash
pip install fastapi tortoise-orm jinja2 python-multipart
# install this package (local path or pip)
pip install -e .
```

```python
# app.py
from fastapi import FastAPI
from admin.core.site import AdminSite
from admin.core.boot import register_startup  # seeds defaults + warms cache
from admin.core.template_provider import TemplateProvider

app = FastAPI()

site = AdminSite(template_provider=TemplateProvider())
# Register your admins here (see example below)

# Mount the admin under /panel
app.include_router(site.build_router(prefix="/panel"))

# Ensure settings defaults are seeded and cache is loaded at startup
register_startup(app)
```

Run the app and open `http://localhost:8000/panel/`.

---

## Architecture

* **AdminSite (Core/Coordinator)**
  Slim registry of model admins, content-type map, route composition. No domain logic.
* **PageRegistry**
  Knows about ORM/Settings registrations, menu tree, unique paths.
* **CrudRouterBuilder**
  Builds CRUD for `/orm/...` and `/settings/...` prefixes with consistent permission dependencies.
* **ApiController**
  `/api/schema`, `/api/uiconfig`, `/api/list_filters`, `/api/autocomplete` — proxied to the relevant `BaseModelAdmin`, auth via `Depends` (`view`).
* **TemplateProvider**
  Ships templates and static assets; `AdminSite` is path-agnostic.
* **BaseModelAdmin (Domain)**

  * JSON-Schema + UI schema; server-side validation
  * List/filters/columns
  * Query hooks: `get_base_queryset`, `get_list_queryset`, `get_object_queryset`,
    `apply_select_related/only`, `apply_row_level_security`
  * Business/UI hook: `allow(user, action, obj=None)`
* **Adapter (Tortoise)**
  Model introspection → descriptor (fields, types, relations).

---

## Registering admins

`AdminSite.register` has **one** clear signature:

```python
site.register(
    app: str,
    model: type,                 # Tortoise ORM model
    admin_cls: type,             # subclass of BaseModelAdmin
    *,
    settings: bool = False,      # register under /settings
    icon: str | None = None,     # Bootstrap icon class (e.g., "bi-gear")
    name: str | None = None      # display name
)
```

Example — register a settings model in the **Settings** area:

```python
from admin.core.site import AdminSite
from admin.core.base import BaseModelAdmin
from myapp.models import SystemSetting

class SystemSettingAdmin(BaseModelAdmin):
    class Meta:
        pass  # columns/filters as needed

site.register(
    app="core",
    model=SystemSetting,
    admin_cls=SystemSettingAdmin,
    settings=True,
    icon="bi-gear",
    name="System Settings",
)
```

---

## System configuration

The admin uses a **key–value settings store** backed by DB.

* **Keys** live in `SettingsKey(StrChoices)` (one enum to rule them all).
* **Defaults** live in `DEFAULT_SETTINGS: dict[SettingsKey, (value, type)]`.
* **SystemConfig** is the access layer.

At startup we **seed missing keys** and **warm the cache**:

```python
from admin.core.boot import register_startup
register_startup(app)  # ensure_seed() + reload() on app startup
```

Usage in code:

```python
from admin.core.config import system_config
from admin.core.keys import SettingsKey

title = await system_config.get(SettingsKey.DEFAULT_ADMIN_TITLE)
per_page = system_config.get_cached(SettingsKey.DEFAULT_PER_PAGE, 20)  # cache-only, after startup
```

> Old hardcoded constants are **deprecated**. Always read through `system_config`.

---

## Permissions (RBAC)

* **Model-scoped**: `view`, `add`, `change`, `delete` (for ORM area)
* **Global-scoped**: `view`, `change` (for Settings area)
* Enforced via FastAPI dependencies:

  * `require_model_permission(PermAction.view)` etc.
  * `require_global_permission(...)`
* `BaseModelAdmin.apply_row_level_security(qs, user)` for RLS.

---

## Templates & UI

Uniform layout for ORM and Settings:

* **Left**: accordion with apps → models
* **Right**: list/table or form
* **Filters**: off-canvas panel (server-driven schema)

Templates (shipped):

```
templates/
  base.html
  orm.html
  settings.html
  list.html
  form.html
  includes/
    sidebar.html
    section.html
static/
  admin-form.js
  ...
```

JSON-Editor contract from `/api/schema`:

```json
{
  "schema": {
    "type": "object",
    "properties": { ... },
    "required": [ ... ],
    "additionalProperties": false
  },
  "startval": { ... },          // never null
  "schema_version": "1"
}
```

UI assets (widget JS/CSS/partials) are provided via `/api/uiconfig`.

---

## Filters & query syntax

Server-side filters follow a simple pattern:

```
?filter.<field>[__op]=<value>
```

Supported ops depend on field type (`__icontains`, `__in`, `__gte`, etc.).
The filter panel is rendered from `/api/list_filters` and kept in sync with server logic.

---

## Widgets

Two distinct widget types:

* **Field widgets** (for JSON-Editor fields)

  * Provide `schema_fragment` and `ui_fragment`, plus optional endpoints
* **Free widgets** (Bootstrap cards on pages)

  * Page slots (e.g., `home.main`, `list.right`), data via `initial_data()`

Both share a minimal base for **asset delivery** (JS/CSS/partials) and optional **endpoints** under `/api/widgets/<key>/…`.

---

## Create superuser CLI

Django-style interactive utility:

```bash
# interactive
python -m admin.utils.create_superuser

# non-interactive
python -m admin.utils.create_superuser --no-input \
  --username admin --email admin@example.com --password secret

# update existing
python -m admin.utils.create_superuser --username admin --update-if-exists --reset-password-if-exists --no-input --password newpass
```

* Prompts for username/email/password (with confirmation).
* `--no-input` + env (`ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`) supported.
* Uses the same PBKDF2 hashing settings as the admin (`SystemConfig` → `security.password_*`).

---

## Roadmap

* **Widgets**

  * Default field widgets: `text`, `textarea`, `boolean`, `number`, `select`, `autocomplete`, `datetime`, `date`, `time`
  * Free widgets: dashboard cards, list-right panels
* **UX sugar**

  * Active filter chips, badges, friendly empty states
  * Choice/bool/datetime formatting, `choices_map` in `columns_meta`
* **Performance**

  * QS profiling hooks, explicit `select_related/only` helpers
* **Docs & packaging**

  * Detailed `BaseModelAdmin` contracts, examples, cookbook
* **Testing**

  * Smoke tests: RBAC matrix, schema snapshot, RLS, ORM/Settings routers

---

## License

MIT — do what you want, just keep the copyright.

---

## Credits
This work is built brick by brick and released as real Open Source.  If you find it useful, help me ship the next bricks faster, you can support the development via [GitHub Sponsors](https://github.com/sponsors/your-username).
I’m committed to production-grade, documented, and maintained tools.  Your support funds tests, docs, and releases.

