# -*- coding: utf-8 -*-
"""Application configuration primitives for the FreeAdmin core.

Provide a unified configuration object shared by applications, agents and
services.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import importlib
from typing import ClassVar, Sequence


class AppConfig:
    """Represent metadata and hooks for an application package."""

    name: ClassVar[str | None] = None
    app_label: ClassVar[str]
    connection: ClassVar[str] = "default"
    models: ClassVar[Sequence[str]] = ()

    def __init__(self) -> None:
        """Validate configuration attributes and derive defaults."""

        label = getattr(self.__class__, "app_label", "")
        if not label:
            raise ValueError("AppConfig subclasses must define a non-empty 'app_label'")
        self._app_label = label
        self._name = getattr(self.__class__, "name", None) or self.__module__.rsplit(".", 1)[0]
        self._connection = getattr(self.__class__, "connection", "default") or "default"
        self._models = tuple(getattr(self.__class__, "models", ()) or ())

    @property
    def import_path(self) -> str:
        """Return the dotted Python import path of the application package."""

        return self._name

    @property
    def app_label(self) -> str:
        """Return the short label associated with the application."""

        return self._app_label

    @property
    def db_connection(self) -> str:
        """Return the database connection label assigned to the application."""

        return self._connection

    def get_models_modules(self) -> list[str]:
        """Return modules that expose ORM models for the application."""

        return list(self._models)

    @classmethod
    def load(cls, module_path: str) -> "AppConfig":
        """Import an application module and return its ``AppConfig`` instance."""

        module = importlib.import_module(f"{module_path}.app")
        config = getattr(module, "default", None)
        if not isinstance(config, AppConfig):
            raise TypeError(f"{module_path}.app must define a 'default' AppConfig instance")
        return config


__all__ = ["AppConfig"]


# The End

