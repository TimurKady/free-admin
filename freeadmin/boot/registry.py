# -*- coding: utf-8 -*-
"""
boot.registry

Utility helpers for bootstrapping the admin app.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Iterable

from ..core.app import AppConfig


class ModelModuleRegistry:
    """Track adapter and app-specific model modules for registration."""

    def __init__(self) -> None:
        self._configs: dict[str, AppConfig] = {}
        self._modules_by_label: dict[str, set[str]] = {}
        self._registered: dict[str, set[str]] = {}

    def register_base(self, app_label: str, modules: Iterable[str]) -> None:
        """Record adapter-provided ``modules`` for ``app_label``."""

        if not modules:
            return
        self._modules_by_label.setdefault(app_label, set()).update(modules)

    def register_config(self, config: AppConfig) -> None:
        """Store ``config`` and record its model modules."""

        key = config.import_path
        if key in self._configs:
            return
        self._configs[key] = config
        modules = tuple(config.get_models_modules())
        if not modules:
            return
        self._modules_by_label.setdefault(config.app_label, set()).update(modules)

    def iter_pending(self) -> Iterable[tuple[str, list[str]]]:
        """Yield app labels and modules that still require registration."""

        for app_label, modules in self._modules_by_label.items():
            registered = self._registered.get(app_label, set())
            pending = sorted(module for module in modules if module not in registered)
            if pending:
                yield app_label, pending

    def mark_registered(self, app_label: str, modules: Iterable[str]) -> None:
        """Mark ``modules`` for ``app_label`` as registered."""

        if not modules:
            return
        bucket = self._registered.setdefault(app_label, set())
        bucket.update(modules)

    def clear(self) -> None:
        """Reset stored configuration and registration metadata."""

        self._configs.clear()
        self._modules_by_label.clear()
        self._registered.clear()


# The End

