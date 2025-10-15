# Application Bootstrap Guide

This guide walks you through the process of enabling a new FreeAdmin application from scratch. Follow the numbered steps in order so that the loaders pick up your configuration and execute any services or agents declared by the application module without additional wiring.

## 1. Register the application in settings

1. Open `config/settings.py`.
2. Ensure the module imports `BaseSettings` from `pydantic_settings` so it remains compatible with Pydantic v2.
3. Locate the `Settings` dataclass and append the dotted path of your application package (without the trailing `.app`) to `Settings.INSTALLED_APPS`.
4. Save the file so the importable settings reflect the new entries.

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    INSTALLED_APPS: ClassVar[list[str]] = [
        "core.agents",
        "core.api.sessions",
        "apps.streams",
        "apps.characters",
        "apps.weather",            # <- new application
    ]
```

The loader will import `apps.weather.app` and look for a module-level `default` instance at startup.

## 2. Create the application package

Inside the `apps/` directory create a folder that mirrors the entry added above, e.g. `apps/weather/`. Populate it with:

```
apps/
  weather/
    __init__.py     # re-export public classes only
    app.py          # AppConfig subclass
    service.py      # (optional) background service
    views.py        # (optional) admin or HTTP views
```

`__init__.py` should be limited to re-exporting symbols so that imports remain clean and side-effect free.

Create these files explicitly:

1. `apps/weather/__init__.py` with only the public imports you plan to expose (often re-exporting `WeatherConfig`).
2. `apps/weather/app.py` containing the `AppConfig` subclass described in the next section.
3. Optional modules such as `service.py`, `views.py` or `agents/` packages depending on your feature set.

## 3. Implement `app.py`

Each application exposes an `AppConfig` subclass and a module-level `default` instance. The base class lives in `freeadmin/core/app.py` and validates the configuration when instantiated. Create `apps/weather/app.py` with the following structure:

```python
# apps/weather/app.py
from freeadmin.core.app import AppConfig
from core.services.registry import ServiceRegistry  # project-specific registry helper
from .service import WeatherService


class WeatherConfig(AppConfig):
    """Register weather dashboards and background collectors."""

    app_label = "weather"
    name = "apps.weather"
    connection = "analytics"      # optional DB routing label
    models = ("apps.weather.models",)

    def __init__(self) -> None:
        """Instantiate helpers used throughout the application."""
        super().__init__()
        self.service = WeatherService()

    async def startup(self) -> None:
        """Register the weather service and perform initial sync."""
        await self.service.startup()
        ServiceRegistry.register(self.service.name, self.service)


default = WeatherConfig()
```

Expose the `default` variable at module scope—the loader requires it to access the configuration object. When the loader imports `apps.weather.app`, it expects to find a ready-to-use configuration instance that defines any initialization hooks you rely on.

## 4. Understand `AppConfig`

`AppConfig` centralizes metadata for all application types. Understanding each attribute clarifies how the framework discovers, initializes and coordinates your package:

| Member | Purpose | When to override |
| --- | --- | --- |
| **`app_label`** | Short identifier used by admin modules, registries and metrics. | Always override. Use a concise, unique label. |
| **`name`** | Full dotted path of the package. Defaults to the module portion of `app.py` if omitted. | Override when the package lives outside the standard layout or you re-export config from another module. |
| **`connection`** | Database connection label stored on the configuration instance. Defaults to `"default"`. | Override when the app writes to a non-default database or analytical replica. |
| **`models`** | Iterable of dotted modules that contain ORM models. Kept as a class attribute for discovery helpers. | Override when the ORM models are split across multiple modules. |
| **`load(module_path)`** | Class method that imports `<module_path>.app`, extracts `default` and verifies it is an `AppConfig` instance. | Rarely override—custom loaders may subclass `AppConfig` and extend the logic if necessary. |

These pieces ensure a consistent lifecycle regardless of whether you configure an admin view, agent or background worker. During `__init__`, the base class validates that `app_label` exists, normalizes the package path and captures database routing rules so other components can reference them later via the `connection` attribute.

## 5. Configure optional services

Applications that manage long-running processes should provide a service class (typically under `service.py`) that cooperates with `ServiceRegistry`.

1. Subclass `core.services.base.BaseService` to implement the behavior.
2. Instantiate the service inside your `AppConfig.__init__` so it is ready by the time initialization hooks run.
3. Register the service inside your configuration's custom `startup()` coroutine (or equivalent) and call its `startup()` method to begin background work.
4. Optionally implement a `shutdown()` coroutine on the service to release resources when the application stops.

```python
# apps/weather/service.py
from core.services.base import BaseService


class WeatherService(BaseService):
    """Stream weather updates from the external provider."""

    name = "weather_stream"

    async def startup(self) -> None:
        """Connect to the provider and prepare caches."""
        ...
```

The FreeAdmin boot sequence will import each module referenced from `Settings.INSTALLED_APPS`, retrieve the `default` configuration instance and execute the initialization coroutine you expose (typically named `startup()`). Remember to pair any startup logic with appropriate teardown in the service when the application stops.

After updating settings and creating the modules above, restart the FreeAdmin application so the loaders re-import configuration objects, then verify that `ServiceRegistry.get("weather_stream")` returns your registered service.

## 6. Wire agents (optional)

If the application introduces agents, mirror the pattern used for services:

1. Create an agent package under `apps/agents/<name>/` with an `app.py` exposing `default`.
2. Use the application `startup()` hook to coordinate with the agent registry if additional setup is required.

By following these steps you ensure every component—apps, services and agents—participates in the FreeAdmin startup sequence without touching additional settings collections.

