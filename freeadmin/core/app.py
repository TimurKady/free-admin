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
        if not isinstance(label, str) or not label:
            raise ValueError("AppConfig subclasses must define a non-empty 'app_label'")
        self.app_label = label

        module_name = self.__class__.name or self.__module__.rsplit(".", 1)[0]
        self.name = module_name

        connection_label = self.__class__.connection or "default"
        self.connection = connection_label

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

