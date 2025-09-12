# FreeAdmin

*Modular admin panel for FastAPI and Tortoise ORM*

## Overview

FreeAdmin is a modern, ORM-agnostic administration panel inspired by Django Admin, but built for the FastAPI ecosystem. It provides a powerful, extensible interface for managing your application data and settings with minimal boilerplate.

## Features

* **Three modes of operation**: ORM CRUD, system configuration panels, and custom views rendered as Bootstrap 5 cards with ready-made HTML (for example, assembled from database queries).
* **JSON-Schema forms** powered by [JSON-Editor](https://github.com/json-editor/json-editor).
* **Role-based access control (RBAC)** with fine-grained permissions at global and model levels.
* **Import/Export wizard** with Excel (via OpenPyXL) and other formats.
* **Inline editing** and reusable widgets.
* **Command-line interface (CLI)** for scaffolding and admin management.
* **Bootstrap 5 frontend** with ready-to-use templates, icons, and static assets.
* **Extensible architecture** with modular adapters for multiple ORMs (starting with Tortoise ORM).

## Architecture

FreeAdmin is organized into clear layers:

* **Core** — AdminSite, PageRegistry, CrudRouterBuilder, authentication and template services.
* **ModelAdmin** — Encapsulates CRUD logic, filters, validation, and ORM bindings.
* **RBAC** — Role and permission system for secure access control.
* **Infrastructure** — ORM adapters, CLI tools, and widget framework.
* **Frontend** — Bootstrap-based UI, JSON-Editor integration, and static assets.

This modular design makes FreeAdmin both powerful and flexible, suitable for projects of any scale.

## Installation

```bash
pip install free-admin
```

### Requirements

* Python 3.10+
* FastAPI
* Tortoise ORM
* PostgreSQL (recommended)

## Quickstart

Here is the minimal setup to get started with FreeAdmin:

```python
from fastapi import FastAPI
from tortoise import Tortoise
from contrib.admin.core.site import AdminSite
from apps.models import Character

app = FastAPI()

# Initialize ORM
Tortoise.init(
    db_url="postgres://user:password@localhost:5432/mydb",
    modules={"models": ["apps.models"]},
)

# Setup admin
admin = AdminSite(app)
admin.register(Character)
```

Run your FastAPI application with Uvicorn:

```bash
uvicorn main:app --reload
```

Then open [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin).

## Documentation

Full documentation is available in the [docs/](docs) folder. Topics include:

* Getting Started
* ModelAdmin API
* RBAC configuration
* Import/Export wizard
* Widgets and Inline forms
* CLI usage
* Advanced customization

## Roadmap

* Support for additional ORMs (SQLAlchemy, GINO).
* Extended set of built-in widgets.
* Multy-nested inline support.
* Internationalization (i18n).

## License

FreeAdmin is **dual-licensed**:

* **AGPL-3.0** (default): You are free to use, modify, and distribute this project under the terms of the GNU Affero General Public License v3.0.
  Any software or service that uses FreeAdmin, including SaaS and internal platforms, **must make its complete source code available under AGPL-3.0**.

* **Commercial License**: Available for organizations that wish to use FreeAdmin without the copyleft requirements of AGPL-3.0.
  This option allows proprietary, closed-source, or commercial use of the software.
  To obtain a commercial license, contact **[timurkady@yandex.com](mailto:timurkady@yandex.com)**.

## Open Source Acknowledgements

FreeAdmin makes use of the following open-source projects:

* [FastAPI](https://fastapi.tiangolo.com/) — web framework.
* [Tortoise ORM](https://tortoise.github.io/) — ORM.
* [Starlette](https://www.starlette.io/) — ASGI toolkit.
* [Pydantic](https://docs.pydantic.dev/) — data validation.
* [Bootstrap 5](https://getbootstrap.com/) — frontend UI.
* [Bootstrap Icons](https://icons.getbootstrap.com/).
* [JSON-Editor](https://github.com/json-editor/json-editor) — JSON Schema editor.
* [Ace Editor](https://ace.c9.io/) — code editor integration.
* [OpenPyXL](https://openpyxl.readthedocs.io/) — Excel support.
* [Click](https://click.palletsprojects.com/) — CLI.
* [Jinja2](https://palletsprojects.com/p/jinja/) — templating.
* [Uvicorn](https://www.uvicorn.org/) — ASGI server.
* [aiofiles](https://github.com/Tinche/aiofiles) — async file I/O.

## Credits

This work is built brick by brick and released as real Open Source.  If you find it useful, help me ship the next bricks faster, you can support the development via [GitHub Sponsors](https://github.com/sponsors/your-username).
I’m committed to production-grade, documented, and maintained tools.  Your support funds tests, docs, and releases.

---

*This project is under active development. Contributions are welcome!*
