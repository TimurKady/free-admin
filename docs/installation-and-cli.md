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
│   └── settings.py    # Pydantic settings model
├── apps/              # Your domain applications
├── pages/             # Optional static/markdown pages
├── static/            # Static assets
├── templates/         # Shared templates
└── README.md          # Short reminder about the scaffold
```

The generated files are intentionally minimal so you can adapt them to your stack.


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

Replace the placeholder in `config/orm.py` with a concrete configuration. The example below initialises Tortoise with a single SQLite database and two application modules:

```python
# config/orm.py
from tortoise import Tortoise


async def init_orm() -> None:
    await Tortoise.init(
        db_url="sqlite:///db.sqlite3",
        modules={
            "models": [
                "apps.blog.models",
            ],
        },
    )
    await Tortoise.generate_schemas()
```

For PostgreSQL or another backend, change `db_url` accordingly (for example `postgres://user:pass@localhost:5432/dbname`).


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


## Step 8. Mount the admin panel

Edit `config/main.py` so it builds the FastAPI application and initialises FreeAdmin via the boot manager:

```python
# config/main.py
from fastapi import FastAPI

from freeadmin.boot import BootManager

from config.orm import init_orm


app = FastAPI(title="My project admin")
boot = BootManager(adapter_name="tortoise")


@app.on_event("startup")
async def startup() -> None:
    await init_orm()


boot.init(app, packages=["apps"])
```

The call to `boot.init()` mounts the admin routes at the path configured by `FA_ADMIN_PATH` (default `/panel`) and schedules background services such as card publishers.


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

Visit `http://127.0.0.1:8000/panel` (or the prefix you configured) and sign in with the credentials created in the previous step. The default interface includes list and detail views for any registered `ModelAdmin`, plus navigation for cards and custom pages.


## Step 12. Troubleshooting tips

* **CLI cannot find `apps/`:** run the command from the project root where the scaffold created the folder.
* **Models not discovered:** ensure the module path (e.g. `apps.blog.models`) is listed in `modules["models"]` when initialising Tortoise.
* **Missing static assets:** verify that `freeadmin.boot.BootManager.init()` has been called and that your ASGI server can serve the mounted static route.
* **Session errors:** set `FA_SESSION_SECRET` to a stable value in production so session cookies remain valid across restarts.

With these steps you now have a working FreeAdmin installation backed by FastAPI and Tortoise ORM. Continue exploring the other documentation chapters for more detail on cards, permissions, and custom views.
