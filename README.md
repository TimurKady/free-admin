# FastAPI FreeAdmin

**Modular admin panel for FastAPI and Tortoise ORM**

[![Tests](https://github.com/TimurKady/freeadmin/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/TimurKady/freeadmin/actions/workflows/ci.yml)
[![Docs](https://readthedocs.org/projects/freeadmin/badge/?version=latest)](https://freeadmin.readthedocs.io/)
[![PyPI](https://img.shields.io/pypi/v/freeadmin.svg)](https://pypi.org/project/freeadmin/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Sponsor](https://img.shields.io/github/sponsors/TimurKady)](https://github.com/sponsors/TimurKady)

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

Behind the scenes the [`freeadmin/`](freeadmin/) directory contains both the Python
modules and bundled static assets. The package structure now mirrors the canonical
`freeadmin` namespace directly, so downstream projects, tooling, and editors can import
modules from `freeadmin.*` without any bootstrap indirection.

## Installation

```bash
pip install freeadmin
```

### Requirements

* Python 3.11+
* FastAPI
* Tortoise ORM
* PostgreSQL (recommended)

## Quickstart

Here is the minimal setup to get started with FreeAdmin:

### 1. Create an Admin class

```python
from freeadmin.core.models import ModelAdmin
from freeadmin.hub import admin_site
from apps.blog.models import Post


class PostAdmin(ModelAdmin):
    """Admin configuration describing how blog posts appear in the panel."""
    list_display = ("id", "title", "created_at")


admin_site.register(Post, PostAdmin)
```

### 2. Mount the panel in the main application

```python
from fastapi import FastAPI
from freeadmin.boot import admin
from my_project.adapters import MyAdapter


app = FastAPI()
admin.init(app, adapter=MyAdapter(), packages=["apps"])
```

### 3. What is `apps`?

The `apps` package is a common convention: each subpackage represents a separate application or domain area (e.g. `apps.blog`, `apps.users`, `apps.orders`).
It’s recommended to place your models inside their respective app folders instead of keeping all models in one large file.

Example structure:

```
my_project/
    apps/
        blog/
            models.py
            admin.py
        users/
            models.py
            admin.py
```

This makes it easier to maintain and scale larger projects.

### 4. Run the server

```bash
uvicorn main:app --reload
```

Then open [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin).

## Documentation

See the [Documentation](https://github.com/TimurKady/freeadmin/blob/main/docs/index.md).

## Roadmap

* Support for additional ORMs (SQLAlchemy, GINO).
* Extended set of built-in widgets.
* Internationalization (i18n).

## License
### FreeAdmin licenses
FreeAdmin is **dual-licensed**:

* **AGPL-3.0** (default): You are free to use, modify, and distribute this project under the terms of the GNU Affero General Public License v3.0.
  Any software or service that uses FreeAdmin, including SaaS and internal platforms, **must make its complete source code available under AGPL-3.0**.

* **Commercial License**: Available for organizations that wish to use FreeAdmin without the copyleft requirements of AGPL-3.0.
  This option allows proprietary, closed-source, or commercial use of the software.
  To obtain a commercial license, contact with [me](https://github.com/TimurKady).

### Third-party licenses

The package depends on and bundles third-party components. When redistributing the project (including deployment in a
SaaS environment) you must retain the notices listed below and keep the referenced license texts available to users.

#### Python runtime dependencies

| Dependency | License | Compliance notes |
| --- | --- | --- |
| FastAPI | MIT | Include the upstream MIT license and copyright notice when redistributing binary or source builds.
| Starlette | BSD-3-Clause | Preserve the BSD disclaimer and copyright notice in any redistributed copies or documentation.
| Jinja2 | BSD-3-Clause | Keep the BSD license text together with any redistributed source/binary artifacts.
| itsdangerous | BSD-3-Clause | Preserve the BSD license notice and warranty disclaimer when shipping the software.
| Tortoise-ORM | Apache-2.0 | Provide the Apache 2.0 license text and propagate any NOTICE file; document local modifications if you change the code.
| python-multipart | Apache-2.0 | Ship the Apache 2.0 license text and carry forward any NOTICE information.
| Pydantic | MIT | Bundle the MIT license text and include attribution in your documentation or “About” page.
| PyJWT | MIT | Keep the MIT license text together with the distributed package.
| openpyxl | MIT | Retain the MIT copyright statement and license grant in redistributed materials.

For MIT-licensed dependencies the standard requirement is to provide the full MIT license and attribution. For the
Apache 2.0 dependencies ensure that the license text and NOTICE file (if present) remain accessible to end users and that
any modifications are documented. BSD-licensed dependencies require preserving their license and disclaimer text.

#### Bundled frontend assets

| Asset | Version | License and source | Compliance notes |
| --- | --- | --- | --- |
| Bootstrap | 5.3.3 | MIT – bundled in `freeadmin/static/vendors/bootstrap/LICENSE` (upstream: <https://github.com/twbs/bootstrap>) | Keep the MIT license reference visible and ship the bundled license file with redistributions.
| Bootstrap Icons | 1.11.3 | MIT – bundled in `freeadmin/static/vendors/bootstrap-icons/LICENSE` (upstream: <https://github.com/twbs/icons>) | Distribute alongside the provided MIT license file.
| jQuery | 3.7.1 | MIT – bundled in `freeadmin/static/vendors/jquery/LICENSE.txt` (upstream: <https://jquery.org/license>) | Retain the header notice and make the MIT license text available via the bundled file.
| JsBarcode | 3.12.1 | MIT – bundled in `freeadmin/static/vendors/jsbarcode/LICENSE` (upstream: <https://github.com/lindell/JsBarcode>) | Preserve the MIT header comments and keep the bundled license file with redistributed builds.
| Select2 | 4.0.13 | MIT – bundled in `freeadmin/static/vendors/select2/LICENSE` (upstream: <https://github.com/select2/select2>) | Bundle the MIT license file and link from documentation where appropriate.
| Choices.js | 11.1.0 | MIT – bundled in `freeadmin/static/vendors/choices/LICENSE` (upstream: <https://github.com/Choices-js/Choices>) | Ship the MIT license file together with the packaged assets.
| Ace (Ace Editor builds) | 1.43.3 | BSD-3-Clause – bundled in `freeadmin/static/vendors/ace-builds/LICENSE` (upstream: <https://github.com/ajaxorg/ace-builds>) | Retain the BSD license text within your documentation or redistribution package.
| JSONEditor | 9.x | MIT – bundled `freeadmin/static/vendors/json-editor/LICENSE` file | Keep the included MIT license file with the distributed assets.

If you update any of the vendor bundles, refresh the version numbers above and bring along their current license files so
that downstream consumers have access to the required texts.

#### Distribution footprint review

To keep release reviews straightforward we periodically record the size of bundled assets and build artifacts:

* `du -sh freeadmin/static` → ~37 MB (vendor assets dominate the total, especially Bootstrap Icons and Ace Editor language/snippet packs).
* `python -m build` produces:
  * Wheel: `dist/freeadmin-0.1.0-py3-none-any.whl` ≈ 7.7 MB.
  * Source archive: `dist/freeadmin-0.1.0.tar.gz` ≈ 6.2 MB.

The sizes are acceptable for the current release cadence, but the Ace and JSONEditor test fixtures remain the largest contributors. If future distributions need to slim down further, consider pruning unused Ace modes/snippets or excluding JSONEditor test pages while keeping the required license files listed above.

## Credits

This work is built brick by brick and released as real Open Source.  If you find it useful, help me ship the next bricks faster, you can support the development via [GitHub Sponsors](https://github.com/sponsors/your-username).
I’m committed to production-grade, documented, and maintained tools.  Your support funds tests, docs, and releases.

---

*This project is under active development. Contributions are welcome!*
