# Configuration

FreeAdmin exposes configuration at two levels:

1. **Application settings** – values specific to your project (databases, debug flags) that you maintain inside `config/settings.py`.
2. **FreeAdmin runtime settings** – values consumed by the admin engine (`FreeAdminSettings`). These can be controlled via environment variables or customised programmatically before initialisation.

This chapter focuses on the second group so you know which environment variables to set and how they affect the admin panel.


## Environment variables

`FreeAdminSettings.from_env()` reads variables with the `FREEADMIN_` prefix. Common entries include:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `FREEADMIN_SECRET_KEY` | `change-me` | Base secret used when other keys are not provided. |
| `FREEADMIN_SESSION_SECRET` | derived from `SECRET_KEY` | Session signing key for the Starlette session middleware. |
| `FREEADMIN_CSRF_SECRET` | derived from `SECRET_KEY` | Secret used to sign CSRF tokens. |
| `FREEADMIN_ADMIN_PATH` | `/panel` | URL prefix where the admin is mounted. |
| `FREEADMIN_MEDIA_URL` | `/media/` | Public prefix for uploaded files. |
| `FREEADMIN_MEDIA_ROOT` | `<cwd>/media` | Filesystem path where uploads are stored. |
| `FREEADMIN_EVENT_CACHE_PATH` | `:memory:` | SQLite file used for caching card payloads (or `:memory:` for in-memory caching). |
| `FREEADMIN_EVENT_CACHE_IN_MEMORY` | inferred | Force in-memory caching even if a path is supplied. |
| `FREEADMIN_JWT_SECRET_KEY` | `None` | Secret used when generating API tokens. |
| `FREEADMIN_ACTION_BATCH_SIZE` | `50` | Maximum number of objects processed per action batch. |
| `FREEADMIN_CARD_EVENTS_TOKEN_TTL` | `3600` | Lifetime (seconds) for card SSE tokens. |
| `FREEADMIN_ADMIN_SITE_TITLE` | `FreeAdmin` | Displayed in the page title and navigation. |
| `FREEADMIN_BRAND_ICON` | empty | Path or URL to the brand icon shown in the header. |
| `FREEADMIN_DATABASE_URL` | `None` | Database DSN used by the bundled Tortoise adapter. |
| `FREEADMIN_STATIC_URL_SEGMENT` | `/static` | URL path for FreeAdmin static assets. |
| `FREEADMIN_STATIC_ROUTE_NAME` | `admin-static` | Route name used when mounting static files. |
| `FREEADMIN_EXPORT_CACHE_PATH` | `<cwd>/freeadmin-export-cache.sqlite3` | SQLite file used for temporary export data. |
| `FREEADMIN_EXPORT_CACHE_TTL` | `300` | Cache lifetime for export artefacts. |

Set these variables before your process starts (for example in a `.env` file, Docker container, or process manager). When a variable is not provided FreeAdmin falls back to sensible defaults and ensures derived values stay consistent (for example `session_secret` defaults to `secret_key`).


## Programmatic configuration

Call `freeadmin.conf.configure()` to install a custom `FreeAdminSettings` instance before the boot manager is created. This is useful when you want to load settings from another source or override a small subset of values without touching environment variables.

```python
from freeadmin.conf import FreeAdminSettings, configure

settings = FreeAdminSettings(
    secret_key="super-secret",
    admin_path="/control",
    brand_icon="/static/images/logo.svg",
)

configure(settings)
```

Every admin component registered after this call receives the customised settings. The boot manager also subscribes to configuration updates so runtime changes propagate to services such as the card cache.


## Integrating with project settings

The scaffolded `config/settings.py` uses `pydantic.BaseSettings` so you can maintain project-specific configuration independently of FreeAdmin. For example:

```python
# config/settings.py
from pydantic import BaseSettings


class ProjectSettings(BaseSettings):
    debug: bool = True
    database_url: str = "sqlite:///db.sqlite3"


settings = ProjectSettings()
```

You can combine both settings layers by exporting `FREEADMIN_DATABASE_URL` from the same `.env` file used by your project settings. FreeAdmin's boot manager will pick up the database URL automatically when initialising the Tortoise adapter.


## Database URL

The bundled Tortoise adapter reads `FREEADMIN_DATABASE_URL`. If the variable is absent FreeAdmin falls back to the value returned by `ProjectSettings.database_url` (if present) or leaves the connection unconfigured. Define the variable explicitly to avoid surprises:

```bash
export FREEADMIN_DATABASE_URL="sqlite:///./db.sqlite3"
```

For PostgreSQL:

```bash
export FREEADMIN_DATABASE_URL="postgres://user:password@localhost:5432/mydb"
```

Ensure the same value is used inside `config/orm.py` when you initialise Tortoise so the CLI commands and your application share the configuration.


## Static and media files

`BootManager` mounts FreeAdmin's bundled static files (Bootstrap, Choices.js, JSONEditor, etc.) at the prefix determined by `FREEADMIN_STATIC_URL_SEGMENT`. Your project-specific assets can live inside the scaffolded `static/` directory. To expose uploaded files, configure `FREEADMIN_MEDIA_ROOT` and `FREEADMIN_MEDIA_URL` – the template provider automatically serves this folder.


## Branding and presentation

Two settings control the visible branding:

* `FREEADMIN_ADMIN_SITE_TITLE` – shown in the `<title>` tag and navigation header.
* `FREEADMIN_BRAND_ICON` – path or URL to an icon displayed in the top-left corner.

Changes are reflected the next time the admin hub is created. If you adjust the settings at runtime, the observer mechanism in `BootManager` propagates the new values to the card manager and menu caches.


## Secrets and security

For production environments:

* Generate a strong `FREEADMIN_SECRET_KEY`. This value seeds all other secrets.
* Consider setting distinct values for `FREEADMIN_SESSION_SECRET` and `FREEADMIN_CSRF_SECRET` to rotate them independently.
* Store secrets in a vault or secret manager rather than committing them to source control.


## Troubleshooting

* **Settings do not change after editing `.env`:** ensure the process reads the file before `BootManager` is imported. The simplest approach is to load environment variables at the top of `config/main.py`.
* **Static files return 404:** verify `FREEADMIN_STATIC_URL_SEGMENT` matches the path registered by `TemplateProvider.mount_static()` and that your ASGI server serves mounted routes.
* **Card updates are lost between restarts:** set `FREEADMIN_EVENT_CACHE_PATH` to a persistent location so the SQLite cache survives restarts, and disable `FREEADMIN_EVENT_CACHE_IN_MEMORY` if necessary.

With these settings in place you can control the admin panel's URL structure, caching behaviour, and security posture without modifying the core library.
