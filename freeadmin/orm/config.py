# -*- coding: utf-8 -*-
"""
config

Declarative ORM configuration helpers for FreeAdmin projects.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, List, Mapping, MutableMapping

from fastapi import FastAPI
from tortoise import Tortoise

from ..adapters import registry


class ORMLifecycle:
    """Manage Tortoise ORM startup and shutdown hooks for FastAPI."""

    def __init__(self, *, config: ORMConfig) -> None:
        """Persist the configuration used to initialise the ORM."""

        self._config = config

    @property
    def adapter_name(self) -> str:
        """Return the name of the adapter that powers the ORM lifecycle."""

        return self._config.adapter_name

    @property
    def modules(self) -> Dict[str, List[str]]:
        """Return the modules mapping supplied to :func:`Tortoise.init`."""

        return self._config.modules

    async def startup(self) -> None:
        """Initialise ORM connections when the FastAPI application boots."""

        await Tortoise.init(
            db_url=self._config.connection_dsn,
            modules=self.modules,
        )

    async def shutdown(self) -> None:
        """Tear down all ORM connections during FastAPI shutdown."""

        await Tortoise.close_connections()

    def bind(self, app: FastAPI) -> None:
        """Attach lifecycle hooks to a FastAPI application instance."""

        app.add_event_handler("startup", self.startup)
        app.add_event_handler("shutdown", self.shutdown)


class ORMConfig:
    """Declarative container for ORM connection and discovery settings."""

    lifecycle_class = ORMLifecycle

    def __init__(
        self,
        *,
        adapter_name: str = "tortoise",
        dsn: str | None = None,
        modules: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        """Store adapter label, connection string, and module declarations."""

        self._adapter_name = adapter_name
        self._dsn = dsn or "sqlite://:memory:"
        self._project_modules = self._normalize_modules(modules or {})
        self._modules = self._merge_adapter_modules(self._project_modules)

    @property
    def adapter_name(self) -> str:
        """Return the name of the registered adapter powering the ORM."""

        return self._adapter_name

    @property
    def connection_dsn(self) -> str:
        """Return the database connection string used for ORM startup."""

        return self._dsn

    @property
    def modules(self) -> Dict[str, List[str]]:
        """Return the module mapping passed to :func:`Tortoise.init`."""

        return deepcopy(self._modules)

    def describe(self) -> dict[str, str]:
        """Return a human-readable summary of the ORM configuration."""

        return {"adapter": self._adapter_name, "dsn": self._dsn}

    def create_lifecycle(self) -> ORMLifecycle:
        """Instantiate an ORM lifecycle manager for FastAPI integration."""

        return self.lifecycle_class(config=self)

    def _normalize_modules(
        self, modules: Mapping[str, Iterable[str]]
    ) -> Dict[str, List[str]]:
        normalized: Dict[str, List[str]] = {}
        for label, values in modules.items():
            normalized[label] = [str(module) for module in values]
        return normalized

    def _merge_adapter_modules(
        self, modules: MutableMapping[str, List[str]]
    ) -> Dict[str, List[str]]:
        merged = deepcopy(modules)
        adapter = registry.get(self._adapter_name)
        adapter_modules = list(getattr(adapter, "model_modules", []))
        project_models = merged.setdefault("models", [])
        for module in adapter_modules:
            if module not in project_models:
                project_models.append(module)
        return merged


__all__ = ["ORMConfig", "ORMLifecycle"]

# The End

