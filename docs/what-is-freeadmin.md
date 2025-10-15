# What is FreeAdmin?

FreeAdmin is an asynchronous administration panel designed for FastAPI projects. It borrows the declarative ergonomics of Django Admin while embracing the async-first ecosystem built around FastAPI and Tortoise ORM.


## A modern take on admin interfaces

Where many admin frameworks are tightly coupled to a specific web stack, FreeAdmin separates concerns:

* **BootManager** integrates with FastAPI and injects the required middleware, discovery hooks, and routers.
* **Adapters** translate ORM operations. The package currently ships with a production-ready Tortoise ORM adapter.
* **AdminSite** keeps registries for models, cards, views, and permissions, exposing a Bootstrap-driven UI.
* **Cards and SSE publishers** provide real-time dashboards without custom wiring.

This modular approach lets you start with a minimal project and grow into complex dashboards without leaving Python.


## Why teams adopt FreeAdmin

* **Async stack alignment.** Everything from CRUD views to background publishers is designed for asyncio.
* **Declarative metadata.** Models, views, cards, and widgets are described with plain Python classes; the runtime handles rendering and routing.
* **FastAPI integration.** The admin is mounted on your existing FastAPI application, sharing its authentication, dependencies, and deployment story.
* **Extensible services.** You can replace adapters, permission services, or template providers without forking the project.


## Typical use cases

* Provide an internal dashboard for a FastAPI + Tortoise application.
* Offer non-technical users a UI to manage database records, run exports, or trigger custom actions.
* Stream live metrics to the admin homepage using server-sent events.
* Prototype an admin panel quickly while keeping the code base open for customisation.


## A quick start snippet

```python
from fastapi import FastAPI

from freeadmin.core.boot import BootManager
from freeadmin.core.interface.models import ModelAdmin
from freeadmin.core.hub import admin_site

from apps.blog.models import Post


class PostAdmin(ModelAdmin):
    """Expose blog posts to the admin UI."""

    list_display = ("title", "created_at")
    search_fields = ("title",)


admin_site.register(app="blog", model=Post, admin_cls=PostAdmin)

app = FastAPI()
boot = BootManager(adapter_name="tortoise")
boot.init(app, packages=["apps"])
```

The example mirrors what the CLI scaffold produces: declare a model admin, register it on the shared `admin_site`, and let `BootManager` mount the admin on your FastAPI application.


## How FreeAdmin differs from Django Admin

* **Framework agnostic runtime.** Instead of depending on Django models and middleware, FreeAdmin interacts with pluggable adapters and Starlette-compatible middleware.
* **Async by default.** The entire stack, from adapters to actions, expects async callables.
* **Explicit discovery.** Packages are discovered through boot-time scanning so you can organise code however you prefer.
* **Lightweight frontend.** Bootstrap 5, Choices.js, and JSONEditor ship pre-bundled; no Node.js build step is required.


## Where to go next

* Read the [core concepts](core-concepts-and-terminology.md) to understand the main classes used throughout the project.
* Follow the [installation guide](installation-and-cli.md) to scaffold a project and mount the admin panel.
* Explore the [architecture overview](architecture-overview.md) for a deeper look at the runtime layers.

FreeAdmin is open source and dual-licensed under AGPL-3.0 and a commercial licence. Contribution ideas include additional adapters, new widgets, and richer documentation examples. If your project needs features not yet available, the modular design makes it straightforward to extend.
