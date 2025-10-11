# -*- coding: utf-8 -*-
"""
boot

Utility helpers for bootstrapping the admin app.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from fastapi import FastAPI
from importlib import import_module
import pkgutil
from starlette.middleware.sessions import SessionMiddleware
from typing import TYPE_CHECKING

from .adapters import BaseAdapter, registry
from .conf import (
    FreeAdminSettings,
    current_settings,
    register_settings_observer,
)

if TYPE_CHECKING:  # pragma: no cover
    from .core.base import BaseModelAdmin
    from .hub import AdminHub


class BootManager:
    """Centralized application boot utilities."""

    def __init__(
        self,
        config=None,
        adapter_name: str | None = None,
        *,
        settings: FreeAdminSettings | None = None,
    ) -> None:
        self._config = config
        self._default_adapter_name = adapter_name
        self._adapter: BaseAdapter | None = None
        self._model_modules: set[str] = set()
        self._hub: "AdminHub | None" = None
        self._settings = settings or current_settings()
        self._system_app: "SystemAppConfig | None" = None
        register_settings_observer(self._handle_settings_update)

    def _ensure_config(self) -> None:
        if self._config is None:
            from .core.settings.config import system_config

            self._config = system_config

    def _ensure_adapter(self) -> None:
        """Load default adapter if configured."""
        if self._adapter is None and self._default_adapter_name is not None:
            self._adapter = self._find_adapter(self._default_adapter_name)
            self._register_model_modules()

    @property
    def adapter(self) -> BaseAdapter:
        """Return the ORM adapter, loading the default if necessary."""
        if self._adapter is None:
            name = self._default_adapter_name
            if name is None:
                raise RuntimeError("Admin adapter not configured")
            self._adapter = self._find_adapter(name)
            self._register_model_modules()
        return self._adapter

    @property
    def user_model(self) -> type | None:
        """Return adapter's user model if available."""
        self._ensure_adapter()
        if self._adapter is None:
            return None
        return getattr(self._adapter, "user_model", None)

    @property
    def model_modules(self) -> list[str]:
        """Return adapter model modules when configured."""
        self._ensure_adapter()
        if self._adapter is None:
            return []
        return getattr(self._adapter, "model_modules", [])

    def get_admin(self, target: str) -> "BaseModelAdmin | None":
        """Return registered admin instance for ``target``."""
        from .hub import admin_site

        try:
            app_label, model_name = target.split(".", 1)
        except ValueError:
            return None
        key = (app_label.lower(), model_name.lower())
        return admin_site.model_reg.get(key)

    def init(
        self, app: FastAPI, adapter: str | None = None, packages: list[str] | None = None
    ) -> None:
        """Initialize the admin application on ``app``."""

        if adapter is not None:
            self._adapter = self._find_adapter(adapter)
            self._register_model_modules()

        from .middleware import AdminGuardMiddleware
        from .core.settings import SettingsKey, system_config

        app.add_middleware(AdminGuardMiddleware)
        session_cookie = system_config.get_cached(
            SettingsKey.SESSION_COOKIE, "session"
        )
        app.add_middleware(
            SessionMiddleware,
            secret_key=self._settings.session_secret,
            session_cookie=session_cookie,
        )

        admin_hub = self._ensure_hub()
        self._ensure_system_app().ready(admin_hub.admin_site)
        admin_hub.init_app(app, packages=packages)

        @app.on_event("startup")
        async def _finalize_admin_site() -> None:
            hub_ref = self._ensure_hub()
            await hub_ref.admin_site.finalize()
            await hub_ref.admin_site.cards.start_publishers()

        self.register_startup(app)
        self.register_shutdown(app)

    def register_startup(self, app: FastAPI) -> None:
        """Register system configuration startup hooks."""

        @app.on_event("startup")
        async def _load_system_config() -> None:
            self._ensure_config()
            await self._config.ensure_seed()
            await self._config.reload()

    def register_shutdown(self, app: FastAPI) -> None:
        """Register shutdown hooks for admin background services."""

        @app.on_event("shutdown")
        async def _stop_card_publishers() -> None:
            hub_ref = self._ensure_hub()
            await hub_ref.admin_site.cards.shutdown_publishers()

    def _find_adapter(self, name: str) -> BaseAdapter:
        """Discover and return an adapter instance by ``name``."""
        package = import_module(".adapters", __package__)
        for _, modname, ispkg in pkgutil.iter_modules(package.__path__):
            if ispkg:
                import_module(f".adapters.{modname}.adapter", __package__)
        return registry.get(name)

    def _register_model_modules(self) -> None:
        """Import adapter-provided model modules once."""
        modules = getattr(self._adapter, "model_modules", [])
        for dotted in modules:
            if dotted not in self._model_modules:
                import_module(dotted)
                self._model_modules.add(dotted)

    def _ensure_hub(self) -> "AdminHub":
        """Return the cached admin hub instance, importing on first access."""
        if self._hub is None:
            from .hub import hub as admin_hub

            self._hub = admin_hub
        return self._hub

    def _ensure_system_app(self) -> "SystemAppConfig":
        """Return the lazily instantiated system application configuration."""

        if self._system_app is None:
            from .apps.system import SystemAppConfig

            self._system_app = SystemAppConfig()
        return self._system_app

    def reset(self) -> None:
        """Restore manager to an uninitialized state."""
        self._config = None
        self._adapter = None
        self._model_modules.clear()
        self._settings = current_settings()

    def _handle_settings_update(self, settings: FreeAdminSettings) -> None:
        """Refresh internal cache whenever global settings are reconfigured."""
        self._settings = settings


admin = BootManager(adapter_name="tortoise")
__all__ = ["BootManager", "admin"]

# The End

