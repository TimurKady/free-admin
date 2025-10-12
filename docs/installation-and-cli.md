# Installation and CLI

*A step‑by‑step guide you can follow with your eyes closed. No prior framework required.*

---

## 0) Prerequisites

* **Python** 3.10+ (3.12 recommended)
* **pip** and **venv** available in PATH
* A terminal: Bash (macOS/Linux) or PowerShell (Windows)

> Tip: Check versions
>
> ```bash
> python --version
> pip --version
> ```

---

## 1) Create and activate a virtual environment

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

> To leave the venv later: `deactivate`

---

## 2) Install FreeAdmin

From PyPI (recommended):

```bash
pip install freeadmin
```

From a local source (if you have a wheel or sdist):

```bash
pip install ./dist/freeadmin-*.whl
# or
pip install ./freeadmin-*.tar.gz
```

---

## 3) Initialize a new project

Create a project skeleton named **`myproject`**:

```bash
freeadmin init myproject
cd myproject
```

You will get:

```
myproject/
├── config/
│   ├── main.py        # Entry point – creates and runs AdminSite
│   ├── orm.py         # ORM bootstrap (SQLite by default in this guide)
│   └── settings.py    # Global settings: INSTALLED_APPS, DEBUG, etc.
├── apps/              # Your business apps live here
├── pages/             # (optional) Static / hybrid pages
├── templates/         # Shared templates
├── static/            # Shared static assets
└── .env               # (optional) environment variables
```

---

## 4) Configure the database (SQLite quickstart)

Open **`config/orm.py`** and put a minimal Tortoise config (example):

```python
# config/orm.py
from tortoise import Tortoise

async def init_orm():
    await Tortoise.init(
        db_url="sqlite://db.sqlite3",
        modules={
            "models": [
                "apps.products.models",  # add your apps here
                "apps.orders.models",
            ]
        },
    )
    await Tortoise.generate_schemas()
```

> You can switch to Postgres later by changing `db_url` (e.g. `postgres://user:pass@localhost:5432/dbname`).

---

## 5) Configure settings

Edit **`config/settings.py`** and list your applications:

```python
# config/settings.py
from dataclasses import dataclass
from typing import ClassVar, List

@dataclass
class Settings:
    DEBUG: bool = True
    LANGUAGE_CODE: str = "en"

    INSTALLED_APPS: ClassVar[List[str]] = [
        "apps.products",
        # "apps.orders",
    ]
```

---

## 6) Create your first app

Generate an app named **`products`**:

```bash
freeadmin add products
```

This creates `apps/products/` with:

```
apps/products/
├── __init__.py
├── app.py         # AppConfig – registers models with AdminSite
├── models.py      # ORM models
├── admin.py       # ModelAdmin / InlineAdmin / Cards / Views
└── (optional: views.py, cards.py, widgets.py)
```

> **Pro tip:** For large apps, group code in `modules/` and import explicitly; do not import `__init__.py` from that folder.

---

## 7) Define a model and its admin

**`apps/products/models.py`**

```python
from tortoise import fields
from tortoise.models import Model

class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    available = fields.BooleanField(default=True)

    class Meta:
        table = "product"
        ordering = ["name"]
```

**`apps/products/admin.py`**

```python
from freeadmin import ModelAdmin
from .models import Product

class ProductAdmin(ModelAdmin):
    list_display = ["name", "price", "available"]
    search_fields = ["name"]
    ordering = ["name"]
```

**`apps/products/app.py`**

```python
from freeadmin import AppConfig
from .models import Product
from .admin import ProductAdmin

class ProductsConfig(AppConfig):
    app_label = "products"
    name = "apps.products"

    def ready(self):
        self.register(Product, ProductAdmin)

default = ProductsConfig()
```

---

## 8) Wire up the AdminSite and run

Open **`config/main.py`** and ensure it loads apps and starts the site:

```python
# config/main.py
import asyncio
from freeadmin import AdminSite
from config.settings import Settings
from config.orm import init_orm

site = AdminSite(title="My Company Admin")

async def bootstrap():
    await init_orm()
    for app in Settings.INSTALLED_APPS:
        site.load(app)
    await site.boot()

if __name__ == "__main__":
    asyncio.run(bootstrap())
    site.run()  # starts the dev server (http://localhost:8000/admin/)
```

Now run it:

```bash
python config/main.py
```

Open **[http://localhost:8000/admin/](http://localhost:8000/admin/)**

---

## 9) Create an admin user (quick bootstrap)

FreeAdmin is framework‑agnostic and does not impose an auth model. For a quick start with Tortoise, you can seed a simple user model **in your own app** and mark it as a superuser. Example sketch:

```python
# apps/users/models.py (example)
from tortoise import fields
from tortoise.models import Model
class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=150, unique=True)
    password_hash = fields.CharField(max_length=255)
    is_superuser = fields.BooleanField(default=False)
```

Add a tiny bootstrap in **`config/orm.py`** after `generate_schemas()`:

```python
from apps.users.models import User
from passlib.hash import bcrypt

async def ensure_superuser():
    if not await User.filter(username="admin").exists():
        await User.create(
            username="admin",
            password_hash=bcrypt.hash("admin123"),
            is_superuser=True,
        )
```

…and call it from `init_orm()`.

> In a real project, plug in your existing auth and permission system. The example above is purely for local testing.

---

## 10) Static assets (front‑end)

FreeAdmin ships with a minimal front‑end stack (Bootstrap 5, jQuery, Choices.js, JSONEditor). If you use vendor files directly, keep them under `static/vendor/` and include in your base template:

```html
<link href="/static/vendor/bootstrap/css/bootstrap.min.css" rel="stylesheet">
<link href="/static/vendor/choices/choices.min.css" rel="stylesheet">
<link href="/static/vendor/select2/css/select2.min.css" rel="stylesheet">
<link href="/static/vendor/bootstrap-icons/bootstrap-icons.css" rel="stylesheet">

<script src="/static/vendor/jquery/jquery-3.7.1.min.js"></script>
<script src="/static/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
<script src="/static/vendor/choices/choices.min.js"></script>
<script src="/static/vendor/ace/src-min-noconflict/ace.js"></script>
<script src="/static/vendor/json-editor/jsoneditor.min.js"></script>
<script src="/static/vendor/jsbarcode/JsBarcode.all.min.js"></script>
```

> You can swap or bundle assets with your own pipeline anytime.

---

## 11) Common pitfalls (read this!)

* **Virtualenv not active** → install lands globally or wrong Python used. Activate `.venv`.
* **App not discovered** → ensure app is listed in `Settings.INSTALLED_APPS` and `app.py` exposes `default`.
* **DB models not loaded** → add your app’s `models` module path to `modules` in `init_orm()`.
* **Import cycles** → don’t import heavy modules in `__init__.py`. Prefer explicit imports and a `modules/` folder.
* **Assets not found** → check your static root/URL and that files exist under `static/`.

---

## 12) Next steps

* Add filters, actions, and inlines to your `ModelAdmin`
* Create custom **Views** and **Cards**
* Integrate your real authentication and permissions
* Switch from SQLite to Postgres

