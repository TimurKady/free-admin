# -*- coding: utf-8 -*-
"""
ORM

Illustrative ORM configuration for the FreeAdmin example project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Dict, List

from fastapi import FastAPI
from tortoise import Tortoise


class ExampleORMConfig:
    """Provide adapter wiring for the FreeAdmin example project."""

    def __init__(
        self,
        *,
        adapter_name: str = "tortoise",
        dsn: str | None = None,
        modules: Dict[str, List[str]] | None = None,
    ) -> None:
        """Store adapter label, connection string, and module mapping."""

        self._adapter_name = adapter_name
        self._dsn = dsn or "sqlite://:memory:"
        self._modules = modules or {
            "models": [
                "example.apps.demo.models",
                "freeadmin.adapters.tortoise.content_type",
                "freeadmin.adapters.tortoise.groups",
                "freeadmin.adapters.tortoise.users",
            ],
        }

    @property
    def adapter_name(self) -> str:
        """Return the name of the ORM adapter in use."""

        return self._adapter_name

    @property
    def connection_dsn(self) -> str:
        """Return the DSN used for the default database connection."""

        return self._dsn

    @property
    def modules(self) -> Dict[str, List[str]]:
        """Return the module mapping passed to :func:`Tortoise.init`."""

        return self._modules

    def describe(self) -> dict[str, str]:
        """Return a human-readable summary of the ORM configuration."""

        return {"adapter": self._adapter_name, "dsn": self._dsn}

    def create_lifecycle(self) -> ExampleORMLifecycle:
        """Instantiate an ORM lifecycle manager for FastAPI integration."""

        return ExampleORMLifecycle(config=self)


class ExampleORMLifecycle:
    """Manage Tortoise ORM startup and shutdown hooks for FastAPI."""

    def __init__(self, *, config: ExampleORMConfig) -> None:
        """Persist the configuration used to initialise the ORM."""

        self._config = config

    @property
    def modules(self) -> Dict[str, List[str]]:
        """Expose the modules configured for Tortoise initialisation."""

        return self._config.modules

    async def startup(self) -> None:
        """Initialise Tortoise ORM connections when FastAPI boots."""

        await Tortoise.init(
            db_url=self._config.connection_dsn,
            modules=self.modules,
        )

    async def shutdown(self) -> None:
        """Close all Tortoise ORM connections during FastAPI shutdown."""

        await Tortoise.close_connections()

    def bind(self, app: FastAPI) -> None:
        """Register lifecycle hooks on a FastAPI application instance."""

        app.add_event_handler("startup", self.startup)
        app.add_event_handler("shutdown", self.shutdown)


__all__ = ["ExampleORMConfig", "ExampleORMLifecycle"]

# The End

