# Configuration

This section explains how to configure FreeAdmin after installation — from environment variables to system settings.
Each step builds on the previous ones, so follow them carefully.

---

## Environment Setup

FreeAdmin can load configuration values from your `.env` file (recommended for local and production environments).

Create a file named `.env` in your project root:

```
DEBUG=True
LANGUAGE_CODE=en
DATABASE_URL=sqlite://db.sqlite3
```

> You can add any variables you need here — they’ll be available through `os.environ` and `Settings`.

---

## The `config/settings.py` file

All global settings are stored in `config/settings.py`. It defines a simple dataclass used across the system.

```python
# config/settings.py
from dataclasses import dataclass
from typing import ClassVar, List
import os

@dataclass
class Settings:
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"
    LANGUAGE_CODE: str = os.getenv("LANGUAGE_CODE", "en")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")

    INSTALLED_APPS: ClassVar[List[str]] = [
        "apps.products",
        # Add other apps here
    ]
```

The `Settings` object acts as the single source of truth for your project. All modules (ORM, AdminSite, etc.) import values from here.

---

## The `config/orm.py` file

`orm.py` contains the ORM initialization and schema generation.

```python
# config/orm.py
from tortoise import Tortoise
from config.settings import Settings

async def init_orm():
    await Tortoise.init(
        db_url=Settings.DATABASE_URL,
        modules={"models": Settings.INSTALLED_APPS},
    )
    await Tortoise.generate_schemas()
```

> ⚠️ **Tip:** Each app’s `models.py` must be importable by Tortoise (e.g. `apps.products.models`).

---

## Customizing the `AdminSite`

You can modify default site settings (title, logo, URL prefix, theme, etc.) directly in `config/main.py`:

```python
from freeadmin import AdminSite

site = AdminSite(
    title="My Company Admin",
    header="FreeAdmin Dashboard",
    url_prefix="/admin/",
    theme="light",
)
```

| Parameter        | Description                                   |
| ---------------- | --------------------------------------------- |
| **`title`**      | Browser window title                          |
| **`header`**     | Page header in admin UI                       |
| **`url_prefix`** | Root path for admin routes                    |
| **`theme`**      | Optional visual theme (e.g., `light`, `dark`) |

---

## Dynamic Configuration

If you need to switch configuration at runtime (e.g., between dev/staging/prod), you can define multiple `.env` files and load them dynamically:

```bash
cp .env .env.production
cp .env .env.staging
```

Then, before starting the project:

```bash
export ENV_FILE=.env.production
```

In `config/settings.py`:

```python
from dotenv import load_dotenv
import os

load_dotenv(os.getenv("ENV_FILE", ".env"))
```

This allows easy environment switching without changing code.

---

## Optional Settings

| Setting             | Type      | Default          | Description                         |
| ------------------- | --------- | ---------------- | ----------------------------------- |
| **`STATIC_ROOT`**   | str       | `static/`        | Where static assets are collected   |
| **`TEMPLATE_DIRS`** | list[str] | `["templates/"]` | Directories to search for templates |
| **`LANGUAGE_CODE`** | str       | `en`             | Default locale                      |
| **`TIME_ZONE`**     | str       | `UTC`            | System timezone                     |
| **`SECRET_KEY`**    | str       | random           | Used for signing sessions and forms |

Example:

```python
from secrets import token_hex

@dataclass
class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", token_hex(32))
```

---

## Changing Database Backends

You can switch from SQLite to PostgreSQL or MySQL by changing `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgres://user:password@localhost:5432/mydb
```

Then re-run migrations or schema generation:

```bash
python config/main.py
```

---

## Configuration Summary

| Component       | File                 | Purpose                               |
| --------------- | -------------------- | ------------------------------------- |
| **Environment** | `.env`               | Global environment variables          |
| **Settings**    | `config/settings.py` | Centralized configuration dataclass   |
| **Database**    | `config/orm.py`      | ORM setup and schema generation       |
| **Admin Site**  | `config/main.py`     | Entry point and runtime customization |


