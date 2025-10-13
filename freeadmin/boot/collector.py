# -*- coding: utf-8 -*-
"""
boot.collector

Utility helpers for bootstrapping the admin app.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from importlib import import_module
import pkgutil
from typing import Callable, Iterable

from ..core.app import AppConfig


class AppConfigCollector:
    """Discover application configs under supplied packages."""

    def __init__(self, register: Callable[[AppConfig], None]) -> None:
        self._register = register
        self._visited: set[str] = set()

    def collect(self, packages: Iterable[str]) -> None:
        """Load app configs exposed by ``packages`` recursively."""

        for package in packages:
            self._walk_package(package)

    def _walk_package(self, package_name: str) -> None:
        if package_name in self._visited:
            return
        self._visited.add(package_name)
        module = self._safe_import(package_name)
        if module is None:
            return
        self._load_config(package_name)
        module_path = getattr(module, "__path__", None)
        if module_path is None:
            return
        prefix = module.__name__ + "."
        for _, name, ispkg in pkgutil.walk_packages(module_path, prefix):
            if ispkg:
                self._walk_package(name)

    def _load_config(self, module_path: str) -> None:
        try:
            config = AppConfig.load(module_path)
        except (ModuleNotFoundError, AttributeError, TypeError, ValueError):
            return
        self._register(config)

    @staticmethod
    def _safe_import(module_name: str):
        try:
            return import_module(module_name)
        except ModuleNotFoundError as exc:
            if getattr(exc, "name", None) == module_name:
                return None
            raise


# The End

