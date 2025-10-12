# Project structure

When you run `freeadmin init` the CLI creates a predictable tree so configuration, discovery, and application code stay organised. This document explains how each folder contributes to the runtime behaviour of FreeAdmin.


## 1. Root layout

A freshly generated project looks like this:

```
myproject/
├── config/
│   ├── main.py
│   ├── orm.py
│   └── settings.py
├── apps/
├── pages/
├── static/
├── templates/
└── README.md
```

Only `config/` contains executable code out of the box. Everything else is ready for you to populate with domain-specific logic, assets, or documentation.


## 2. Configuration package (`config/`)

The `config` package defines how the admin integrates with your FastAPI application and database. The CLI writes minimal placeholders that you are expected to customise:

| File | Purpose |
| ---- | ------- |
| `main.py` | Creates the FastAPI app and should call `BootManager.init()` to mount FreeAdmin. |
| `orm.py` | Holds the Tortoise ORM initialisation logic. |
| `settings.py` | Declares the `ProjectSettings` model backed by `pydantic.BaseSettings`. |

After customisation a typical `main.py` looks like this:

```python
from fastapi import FastAPI

from freeadmin.boot import BootManager

from config.orm import init_orm


app = FastAPI(title="Project administration")
boot = BootManager(adapter_name="tortoise")


@app.on_event("startup")
async def startup() -> None:
    await init_orm()


boot.init(app, packages=["apps"])
```

`boot.init()` wires the admin router, session middleware, and card publishers into the FastAPI application. The list of packages controls autodiscovery: every package listed is scanned for admin registrations.


## 3. Application packages (`apps/<name>/`)

Each folder inside `apps/` represents a logical component of your system. The CLI scaffolder creates empty modules so you can decide how to organise the code:

| File | Typical contents |
| ---- | ---------------- |
| `app.py` | `AppConfig` subclass for startup hooks. |
| `models.py` | Tortoise ORM models. |
| `admin.py` | `ModelAdmin` classes and calls to `admin_site.register`. |
| `views.py` | Optional custom admin views registered with `admin_site.register_view`. |
| `cards.py` | Optional dashboard card registrations. |


A minimal `views.py` might expose a bespoke report page:

```python
from typing import Any

from fastapi import Request

from freeadmin.core.services.auth import AdminUserDTO
from freeadmin.hub import admin_site


@admin_site.register_view(path="/reports/sales", name="Sales report", label="Reports", icon="bi-graph-up")
async def sales_report(request: Request, user: AdminUserDTO) -> dict[str, Any]:
    data = await request.app.state.report_service.fetch_sales_summary()
    return {
        "page_message": "Latest sales metrics.",
        "card_entries": [],
        "context": {"totals": data},
        "assets": {"css": (), "js": ()},
    }
```

`AppConfig` (from `freeadmin.core.app`) lets you run code during discovery or startup. Example:

```python
from freeadmin.core.app import AppConfig
from freeadmin.hub import admin_site

from .admin import PostAdmin
from .models import Post


class BlogConfig(AppConfig):
    app_label = "blog"
    name = "apps.blog"

    async def startup(self) -> None:
        admin_site.register(app="blog", model=Post, admin_cls=PostAdmin)


default = BlogConfig()
```

You can also register models directly inside `admin.py` if you prefer not to use an `AppConfig`. Both patterns are supported.


## 4. Optional folders

* `pages/` – store Markdown or HTML documents and expose them via custom admin views.
* `static/` – add project-specific CSS or JavaScript. The boot manager mounts this directory alongside FreeAdmin's bundled assets.
* `templates/` – override FreeAdmin templates or add new ones used by your custom views.

All three folders are left empty so you can organise them according to your team's conventions.


## 5. Discovery process

During startup `BootManager` invokes the discovery service with the packages you supplied (for example `["apps"]`). Discovery imports each package's `admin.py`, `app.py`, and other modules that register resources on `admin_site`. Once discovery finishes the admin site knows about:

* Model admins declared via `admin_site.register`.
* Standalone views registered with `admin_site.register_view`.
* Cards registered with `admin_site.register_card`.
* Optional startup hooks implemented on `AppConfig.startup()`.

Understanding this flow helps when you need to debug why an admin class is not appearing — ensure the module containing the registration is importable and that the package is listed for discovery.


## 6. Summary

| Area | Location | Notes |
| ---- | -------- | ----- |
| FastAPI integration | `config/main.py` | Instantiates `BootManager` and mounts the admin router. |
| ORM setup | `config/orm.py` | Configures database connections for Tortoise. |
| Environment configuration | `config/settings.py` | Wraps environment variables with a typed settings model. |
| Domain code | `apps/` | Holds models, admins, cards, and optional startup hooks. |
| Presentation assets | `templates/`, `static/` | Extend or override frontend resources. |
| Supplementary content | `pages/` | Provide documentation or helper pages accessible from the admin. |

Following this structure keeps your project organised and makes FreeAdmin's discovery process predictable as your code base grows.
