# Installation and CLI

This guide walks through installing FreeAdmin, generating a project skeleton, and wiring the admin panel into a FastAPI + Tortoise ORM stack. The steps mirror the behaviour of the built-in CLI so the examples match the code that ships with this repository.


## Step 0. Prerequisites

* **Python 3.11+** (the package targets Python 3.11 and newer).
* **pip** and **venv** available on your PATH.
* A database supported by **Tortoise ORM**. SQLite works for local testing; PostgreSQL is recommended for production.

Check your interpreter and pip versions:

```bash
python --version
pip --version
```


## Step 1. Create and activate a virtual environment

**macOS / Linux**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Deactivate later with `deactivate`.


## Step 2. Install FreeAdmin

Install the latest release from PyPI:

```bash
pip install freeadmin
```

You can also install from a local clone by running `pip install .` inside the repository root.


## Step 3. Scaffold a project

Use the CLI to create the base layout:

```bash
freeadmin init myproject
cd myproject
```

The generator creates the following structure:

```
myproject/
├── config/
│   ├── main.py        # FastAPI application factory
│   ├── orm.py         # Placeholder for ORM configuration
│   ├── routers.py     # Provides an aggregator class and helper for admin routes
│   └── settings.py    # Pydantic settings model
├── apps/              # Your domain applications
├── pages/             # Optional static/markdown pages
├── static/            # Static assets
├── templates/         # Shared templates
└── README.md          # Short reminder about the scaffold
```

The generated files are intentionally minimal so you can adapt them to your stack. `config/routers.py` defines `ProjectRouterAggregator` together with a `get_admin_router()` helper. The helper returns a cached `APIRouter` instance so the admin site is not mounted multiple times; call `ProjectRouterAggregator.mount()` if you prefer the class-based API.


## Step 4. Configure project settings

Edit `config/settings.py` to describe your environment. The scaffold uses `pydantic.BaseSettings`, so environment variables automatically override defaults:

```python
# config/settings.py
from pydantic import BaseSettings


class ProjectSettings(BaseSettings):
    debug: bool = True
    database_url: str = "sqlite:///db.sqlite3"


settings = ProjectSettings()
```

If you prefer `.env` files, add `python-dotenv` to your project and call `load_dotenv()` before instantiating `ProjectSettings`.


## Step 5. Configure Tortoise ORM

Replace the placeholder in `config/orm.py` with a concrete configuration. The scaffold generates `ORMSettings` and `ORMLifecycle` classes so you can describe the adapter and then bind lifecycle hooks to FastAPI:

```python
# config/orm.py
from __future__ import annotations

from typing import Dict

from fastapi import FastAPI
from tortoise import Tortoise


class ORMSettings:
    """Provide placeholder ORM configuration values."""

    def __init__(self, *, adapter_name: str = "tortoise") -> None:
        """Store the adapter identifier used by the ORM lifecycle."""

        self._adapter_name = adapter_name

    @property
    def adapter_name(self) -> str:
        """Return the adapter identifier configured for the project."""

        return self._adapter_name

    def template(self) -> Dict[str, str]:
        """Return a dictionary with example ORM configuration."""

        return {"default": "sqlite:///db.sqlite3"}

    def create_lifecycle(self) -> ORMLifecycle:
        """Return an ORM lifecycle configured with these settings."""

        return ORMLifecycle(settings=self)


class ORMLifecycle:
    """Manage ORM startup and shutdown hooks for FastAPI."""

    def __init__(self, *, settings: ORMSettings) -> None:
        """Persist settings required to bind lifecycle handlers."""

        self._settings = settings

    @property
    def adapter_name(self) -> str:
        """Expose the adapter identifier for BootManager wiring."""

        return self._settings.adapter_name

    async def startup(self) -> None:
        """Initialise Tortoise ORM connections when FastAPI boots."""

        config = self._settings.template()
        await Tortoise.init(
            db_url=config["default"],
            modules={"models": ["apps.blog.models"]},
        )

    async def shutdown(self) -> None:
        """Close all Tortoise ORM connections during FastAPI shutdown."""

        await Tortoise.close_connections()

    def bind(self, app: FastAPI) -> None:
        """Register lifecycle handlers on a FastAPI application."""

        app.add_event_handler("startup", self.startup)
        app.add_event_handler("shutdown", self.shutdown)
```

For PostgreSQL or another backend, change the DSN returned from `ORMSettings.template()` and update the module list used during startup.


## Step 6. Create an application package

Generate an app skeleton with the CLI:

```bash
freeadmin add blog
```

This command adds `apps/blog/` containing empty files: `__init__.py`, `app.py`, `models.py`, `admin.py`, `views.py`, and `cards.py`. Fill these modules with your domain logic.

Register the package in your settings or discovery list. With the default scaffold you simply pass `"apps"` to the boot manager so every subpackage under `apps/` is discovered.


## Step 7. Define models and admin classes

Update `apps/blog/models.py` and `apps/blog/admin.py` to describe your data and how it should appear in the admin panel:

```python
# apps/blog/models.py
from tortoise import fields
from tortoise.models import Model


class Post(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    body = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "blog_post"
```

```python
# apps/blog/admin.py
from freeadmin.core.models import ModelAdmin
from freeadmin.hub import admin_site

from .models import Post


class PostAdmin(ModelAdmin):
    """Expose blog posts through the administration panel."""

    list_display = ("title", "created_at")
    search_fields = ("title",)


admin_site.register(app="blog", model=Post, admin_cls=PostAdmin)
```

If you need to run startup logic (for example to register cards or background publishers) create `apps/blog/app.py` and expose a `default` instance of `freeadmin.core.app.AppConfig`.


## Step 8. Review the generated bootstrap

`freeadmin init` now scaffolds a `config/main.py` that already wires the boot manager, binds the ORM lifecycle through `ORMLifecycle.bind()`, and initialises FreeAdmin with sensible defaults:

```python
# config/main.py
from collections.abc import Iterable
from typing import List

from fastapi import FastAPI
from freeadmin.boot import BootManager

from .orm import ORMLifecycle, ORMSettings
from .settings import ProjectSettings


class ApplicationFactory:
    """Create FastAPI applications for the project."""

    def __init__(
        self,
        *,
        settings: ProjectSettings | None = None,
        orm_settings: ORMSettings | None = None,
        packages: Iterable[str] | None = None,
    ) -> None:
        self._settings = settings or ProjectSettings()
        self._orm_settings = orm_settings or ORMSettings()
        self._orm_lifecycle: ORMLifecycle = self._orm_settings.create_lifecycle()
        self._boot = BootManager(adapter_name=self._orm_lifecycle.adapter_name)
        self._app = FastAPI(title=self._settings.project_title)
        self._packages: List[str] = list(packages or ["apps", "pages"])
        self._orm_events_bound = False

    def build(self) -> FastAPI:
        """Return a FastAPI instance wired with FreeAdmin integration."""

        self._bind_orm_events()
        self._boot.init(
            self._app,
            adapter=self._orm_lifecycle.adapter_name,
            packages=self._packages,
        )
        return self._app

    def _bind_orm_events(self) -> None:
        """Attach ORM lifecycle hooks to the FastAPI application."""

        if self._orm_events_bound:
            return
        self._orm_lifecycle.bind(self._app)
        self._orm_events_bound = True


app = ApplicationFactory().build()
```

The default discovery packages (`apps` and `pages`) match the directories created by the CLI, so FreeAdmin autodiscovers model admins and content pages without further configuration. Pass a different `packages` iterable to `ApplicationFactory` when you need to customise discovery. Update `config/orm.py` to implement real startup and shutdown hooks; the scaffolded `ORMLifecycle` class already binds them against FastAPI.

To mount the admin interface without double registration, create a `ProjectRouterAggregator` and call `mount()` during application setup:

```python
from fastapi import FastAPI
from freeadmin.hub import admin_site

from config.routers import ProjectRouterAggregator


class ApplicationFactory:
    def __init__(self) -> None:
        self._routers = ProjectRouterAggregator()

    def build(self) -> FastAPI:
        app = FastAPI()
        self._routers.mount(app, admin_site)
        return app
```

`config/routers.py` continues to aggregate router registrations. Import `get_admin_router()` when you only need the router instance, or reuse `ProjectRouterAggregator.mount()` inside `config/main.py` if you want to include the admin and auxiliary routers together while avoiding duplicate mounts.


## Step 9. Configure the database URL

FreeAdmin reads `FA_DATABASE_URL` when using the bundled Tortoise adapter. Export the variable or set it in your process manager before running the app:

```bash
export FA_DATABASE_URL="sqlite:///./db.sqlite3"
```

For PostgreSQL use a DSN such as `postgres://user:password@localhost:5432/mydb`.


## Step 10. Create an admin user

The CLI can create superusers for the bundled authentication models:

```bash
freeadmin create-superuser --username admin --email admin@example.com
```

If you omit the flags the command will prompt for the missing values. It initialises the ORM, ensures the auth tables exist, and stores the user record using the active adapter.


## Step 11. Run the development server

Use Uvicorn (or your ASGI server of choice) to run the FastAPI application:

```bash
uvicorn config.main:app --reload
```

Visit `http://127.0.0.1:8000/admin` (or the prefix you configured) and sign in with the credentials created in the previous step. The default interface includes list and detail views for any registered `ModelAdmin`, plus navigation for cards and custom pages.


## Step 12. Troubleshooting tips

* **CLI cannot find `apps/`:** run the command from the project root where the scaffold created the folder.
* **Models not discovered:** ensure the module path (e.g. `apps.blog.models`) is listed in `modules["models"]` when initialising Tortoise.
* **Missing static assets:** verify that `freeadmin.boot.BootManager.init()` has been called and that your ASGI server can serve the mounted static route.
* **Session errors:** set `FA_SESSION_SECRET` to a stable value in production so session cookies remain valid across restarts.

With these steps you now have a working FreeAdmin installation backed by FastAPI and Tortoise ORM. Continue exploring the other documentation chapters for more detail on cards, permissions, and custom views.
