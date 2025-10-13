# -*- coding: utf-8 -*-
"""
main

Example application bootstrap for FreeAdmin.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import List

from fastapi import FastAPI

from freeadmin.boot import BootManager

from .orm import ExampleORMConfig, ExampleORMLifecycle
from .routers import ExampleAdminRouters
from .settings import ExampleSettings


class ExampleApplication:
    """Assemble a runnable FreeAdmin demonstration project."""

    def __init__(
        self,
        *,
        settings: ExampleSettings | None = None,
        orm: ExampleORMConfig | None = None,
    ) -> None:
        """Store configuration helpers and prepare the FastAPI app."""

        self._settings = settings or ExampleSettings()
        self._orm = orm or ExampleORMConfig()
        self._orm_lifecycle: ExampleORMLifecycle = self._orm.create_lifecycle()
        self._boot = BootManager(adapter_name=self._orm.adapter_name)
        self._app = FastAPI(title=self._settings.project_name)
        self._packages: List[str] = []
        self._routers = ExampleAdminRouters()
        self._orm_events_bound = False

    def register_packages(self, packages: Iterable[str]) -> None:
        """Register Python packages that expose admin resources."""

        for package in packages:
            package_name = str(package)
            if package_name not in self._packages:
                self._packages.append(package_name)

    def configure(self) -> FastAPI:
        """Configure FreeAdmin integration and return the FastAPI app."""

        discovery_packages = self._packages or [
            "example.apps",
            "example.pages",
        ]
        if not self._orm_events_bound:
            self._orm_lifecycle.bind(self._app)
            self._orm_events_bound = True
        self._boot.init(
            self._app,
            adapter=self._orm.adapter_name,
            packages=discovery_packages,
        )
        self._routers.mount(self._app)
        return self._app

    @property
    def app(self) -> FastAPI:
        """Return the FastAPI application managed by the example."""

        return self._app

    @property
    def boot_manager(self) -> BootManager:
        """Expose the underlying boot manager for customization."""

        return self._boot


__all__ = ["ExampleApplication"]

# The End

