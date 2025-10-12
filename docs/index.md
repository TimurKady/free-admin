# FastAPI FreeAdmin

Welcome to the FreeAdmin documentation. This guide focuses on the new documentation set that ships with the repository.

**FreeAdmin** is a modular administration system for **FastAPI** projects that use the asynchronous **Tortoise ORM**. The runtime is split into small, well-defined services so you can tailor registrations, permissions, and UI composition without leaving Python.

The default distribution ships with:

* A Bootstrap 5 powered interface rendered through Jinja2 templates.
* Automatic CRUD scaffolding for models registered on the admin site.
* Real-time dashboard cards delivered over server-sent events.
* A FastAPI integration layer driven by `BootManager`, which wires the admin router, middleware, and background tasks into your application.

Custom adapters can be added, but the package currently provides a production-ready adapter for **Tortoise ORM** out of the box.


## Why FreeAdmin

FreeAdmin was designed for teams that enjoy the declarative ergonomics of Django Admin but need an asynchronous stack and finer control over routing and discovery.

* **Declarative metadata.** Admin classes describe columns, filters, cards, and views; the runtime handles persistence and rendering.
* **Composable services.** The hub, router, permission checker, and card manager are pluggable components that can be swapped or extended.
* **FastAPI-first.** The admin site is mounted directly on your FastAPI application, sharing middleware and dependency injection patterns.
* **Async by default.** Adapters, actions, and background publishers run with asyncio-friendly interfaces.


## How the pieces connect

The boot sequence starts with `BootManager`, which loads the configured adapter, initialises discovery, and mounts the admin router on your FastAPI instance. Once initialised, the `AdminSite` keeps a registry of:

* Model admins and their CRUD routes.
* Standalone admin views and menu entries.
* Dashboard and inline cards with their background publishers.
* Settings pages backed by the system configuration service.

The architecture layers are described in detail in the [Architecture overview](architecture-overview.md).


## Essential topics

Start with the following chapters to assemble a working project:

* [What is FreeAdmin?](what-is-freeadmin.md) – conceptual background and use cases.
* [Core concepts and terminology](core-concepts-and-terminology.md) – a tour of the main classes you will interact with.
* [Installation and CLI](installation-and-cli.md) – how to install the package, generate a scaffold, and run the admin panel.
* [Project structure](project-structure.md) – how the scaffolded files fit together.
* [Configuration](configuration.md) – adapting settings and database configuration.

Additional references:

* [Release review checklist](release-review.md) – artefact verification steps for maintainers.


## Road ahead

Active development is focused on:

* Additional widgets for common form patterns.
* Expanded card publishers with richer SSE tooling.
* Improved configuration helpers for multi-database projects.
* Reference adapters for other ORMs once their integration layers are production ready.

You can explore the example project under `example/` to see the components working together.

