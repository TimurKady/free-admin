# Quick Start

This guide walks through the minimal steps required to scaffold a FreeAdmin project, connect it to a database, and expose the administration interface. The workflow mirrors the behaviour of the bundled CLI utilities and the runtime boot sequence shipped with the package.

## Project layout conventions

Running ``freeadmin init`` creates a predictable skeleton consisting of shared directories and pre-filled configuration modules:

- ``config/`` stores ``main.py``, ``orm.py``, and ``settings.py``. These templates provide a FastAPI entry point, an ORM configuration placeholder, and a Pydantic settings object respectively.
- ``apps/`` contains domain-specific applications. The ``add`` command populates each app with ``app.py``, ``models.py``, ``admin.py``, ``views.py``, and ``cards.py`` stubs plus an ``__init__.py`` marker.
- ``pages/``, ``static/``, and ``templates/`` are provisioned for custom dashboards, static assets, and HTML overrides.

Every generated file includes headers and docstrings that explain the intended customisation points; keep these modules in place so that autodiscovery can locate admin registrations.

## Installation

Install FreeAdmin together with FastAPI, Tortoise ORM, and an ASGI server. Uvicorn is used in the examples:

```bash
pip install freeadmin fastapi tortoise-orm uvicorn
```

Set the database URL through the ``FREEADMIN_DATABASE_URL`` environment variable (or ``FREEADMIN_DATABASE_URL``/``DATABASE_URL`` in ``.env`` files) so that both the admin runtime and management commands can open ORM connections.

## 1. Initialise a project skeleton

Use the CLI ``init`` command to scaffold a new project directory. The command accepts an optional project name; if omitted, ``myproject`` is used.

```bash
freeadmin init demo_admin
cd demo_admin
```

After running the command you should see the directories described in the previous section. Re-running ``init`` is idempotent—the command reports any existing files it keeps in place.

## 2. Configure application and database settings

Open ``config/settings.py`` and adjust defaults such as the project title or database DSN. The generated ``ProjectSettings`` class exposes typed attributes that can be read throughout your project. Environment variables prefixed with ``FREEADMIN_`` override these values automatically at runtime.

Update ``config/orm.py`` to describe your database connection. The placeholder ``ORMSettings`` class is intended for your adapter-specific configuration values—for Tortoise ORM you can include module paths that should be registered during startup.

## 3. Mount FreeAdmin on FastAPI

Edit ``config/main.py`` so the FastAPI application initialises FreeAdmin's boot manager. The default boot manager ships with the Tortoise adapter pre-configured, so calling ``admin.init`` with the packages that should be auto-discovered is sufficient.

```python
from fastapi import FastAPI
from freeadmin.boot import admin

app = FastAPI(title="Demo Admin")
admin.init(app, packages=["apps"])
```

Placing your admin modules under ``apps/<app_name>/admin.py`` ensures they are discovered when FreeAdmin scans the listed packages.

## 4. Add an application module

Within the project root run the ``add`` command to create a new application package inside ``apps``. The command must be executed where the ``apps`` directory exists; otherwise it exits with a helpful message.

```bash
freeadmin add blog
```

Populate ``apps/blog/models.py`` with your ORM models and ``apps/blog/admin.py`` with the admin configuration. For example, a simple Tortoise model and admin registration could look like this:

```python
from tortoise import fields
from tortoise.models import Model

from freeadmin.core.models import ModelAdmin
from freeadmin.hub import admin_site


class Post(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    body = fields.TextField()
    published_at = fields.DatetimeField(null=True)

    class Meta:
        app = "blog"
        table = "blog_posts"


class PostAdmin(ModelAdmin):
    """Expose blog posts in the administration interface."""

    list_display = ("id", "title", "published_at")
    search_fields = ("title",)


admin_site.register(app="blog", model=Post, admin_cls=PostAdmin)
```

The ``register`` call matches the runtime signature expected by ``AdminSite`` and adds the model to the navigation menu and API registry.

## 5. Prepare the database and superuser

Before you can sign in, run your migrations and create an administrative user. FreeAdmin ships with a ``create-superuser`` command that prompts for credentials or reads them from flags/environment variables.

```bash
export FREEADMIN_DATABASE_URL="sqlite:///./db.sqlite3"
freeadmin create-superuser
```

The command initialises the ORM using the configured adapter, ensures system settings are seeded, and then creates or updates the requested user account.

## 6. Run the server

Start the ASGI server using Uvicorn and point it at the FastAPI app defined in ``config/main.py``:

```bash
uvicorn config.main:app --reload
```

Once the application boots, open ``http://127.0.0.1:8000/panel`` (or the path defined by ``FREEADMIN_ADMIN_PATH``) to access the FreeAdmin interface.

This completes the minimal setup. From here you can explore additional documentation under the ``docs/admin`` directory for advanced configuration topics such as adapters, widgets, cards, and RBAC.
