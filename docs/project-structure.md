# Project and App Structure

When you create a new FreeAdmin project with `freeadmin init`,  
the CLI generates a predictable, modular layout that separates **core configuration** from **applications**.

## 1. Generated Project Layout

A typical project after initialization looks like this:

```

myproject/
├── config/                 # Project configuration and bootstrap code
│   ├── main.py             # Entry point (creates and runs the AdminSite)
│   ├── orm.py              # ORM initialization (Tortoise or another backend)
│   └── settings.py         # Global settings (apps, language, debug)
│
├── apps/                   # Business-domain applications
│   ├── products/
│   │   ├── **init**.py
│   │   ├── app.py          # Application registration and metadata
│   │   ├── models.py       # ORM models for this app
│   │   ├── admin.py        # ModelAdmin, InlineAdmin, Cards, Views
│   │   ├── views.py        # Optional: custom views
│   │   └── cards.py        # Optional: dashboard cards
│   └── orders/
│       ├── app.py
│       └── models.py
│
├── pages/                  # Optional: static or hybrid pages (HTML/Markdown)
├── templates/              # Shared templates
├── static/                 # Shared static assets
└── .env                    # Environment configuration (optional)

````

---

## 2. Core Folder: `config/`

The **`config/`** directory defines the project itself — not an app,  
but the bootstrap logic that initializes and runs the admin system.

| File | Purpose |
|------|----------|
| **`settings.py`** | Holds configuration like `INSTALLED_APPS`, language, debug flag, and other constants. |
| **`orm.py`** | Configures the ORM (e.g. Tortoise) and connects it to your database. |
| **`main.py`** | Entry point. Creates the `AdminSite`, loads all apps, and runs the development server. |

Example:
```python
# config/main.py
from freeadmin import AdminSite
from config.settings import Settings

site = AdminSite(title="My Company Admin")

for app in Settings.INSTALLED_APPS:
    site.load(app)

if __name__ == "__main__":
    site.run()
````

---

## 3. Application Folder: `apps/<name>/`

Each folder inside `apps/` represents an **independent application**.
Applications are where your models, admin logic, and optional views live.

| File             | Purpose                                                                    |
| ---------------- | -------------------------------------------------------------------------- |
| **`app.py`**     | Defines `AppConfig` and registers models with the admin.                   |
| **`models.py`**  | Contains ORM model definitions.                                            |
| **`admin.py`**   | Declares admin metadata: `ModelAdmin`, `InlineAdmin`, `Card`, `View`, etc. |
| **`views.py`**   | (Optional) Custom admin or user-facing views.                              |
| **`cards.py`**   | (Optional) Dashboard or model-related cards.                               |
| **`widgets.py`** | (Optional) Custom form widgets or UI components.                           |

Each `app.py` file must expose a variable named `default` —
this is how FreeAdmin automatically discovers and registers applications.

Example:

```python
# apps/products/app.py
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

## 4. Optional Folder: `pages/`

`pages/` is an optional directory at the root of your project.
It can contain static or semi-dynamic pages such as:

* documentation pages,
* help or policy content,
* or lightweight dashboards not tied to a specific app.

Each page can be written in HTML, Markdown, or Jinja2,
and rendered through a dedicated `PageView`.

---

## 5. Why This Layout Matters

FreeAdmin uses discovery rather than configuration files:
when `AdminSite.boot()` runs, it automatically:

1. Loads apps from `Settings.INSTALLED_APPS`
2. Imports their `app.py`
3. Registers models and admin definitions
4. Initializes ORM via `config/orm.py`
5. Launches the web interface

This convention ensures that every project — small or large — remains consistent and predictable.

---

## 6. Summary

| Type            | Defined In     | Description                                              |
| --------------- | -------------- | -------------------------------------------------------- |
| **Project**     | `config/`      | Contains core logic (`main.py`, `orm.py`, `settings.py`) |
| **Application** | `apps/<name>/` | Encapsulates business logic and admin definitions        |
| **Page Layer**  | `pages/`       | Optional presentation content outside app structure      |

---


