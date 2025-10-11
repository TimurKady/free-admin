# -*- coding: utf-8 -*-
"""
discovery

Admin discovery utilities for modules, views, and services.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from types import ModuleType
from typing import Iterable, List, Set


class DiscoveryService:
    """Manage discovery of admin modules, views, and publisher services."""

    logger = logging.getLogger(__name__)

    def __init__(self) -> None:
        """Initialize the discovery service without persistent state."""

        pass

    def discover_admin_modules(self, packages: Iterable[str]) -> None:
        """Import ``*.admin`` modules within the provided ``packages``."""

        roots = self._collect_package_roots(packages)
        self._import_admin_modules(roots)

    def discover_views(self, packages: Iterable[str]) -> None:
        """Import view modules or packages within the provided ``packages``."""

        roots = self._collect_package_roots(packages)
        self._import_named_modules(roots, "views")

    def discover_services(self, packages: Iterable[str]) -> None:
        """Import publisher services within ``packages``."""

        roots = self._collect_package_roots(packages)
        for suffix in ("service", "services"):
            self._import_named_modules(roots, suffix)

    def discover_all(self, packages: Iterable[str]) -> None:
        """Import admin modules, views, and services within ``packages``."""

        roots = self._collect_package_roots(packages)
        self._import_admin_modules(roots)
        self._import_named_modules(roots, "views")
        for suffix in ("service", "services"):
            self._import_named_modules(roots, suffix)

    def _collect_package_roots(self, packages: Iterable[str]) -> List[ModuleType]:
        roots: List[ModuleType] = []
        seen: Set[str] = set()
        for pkg in packages:
            if pkg in seen:
                continue
            seen.add(pkg)
            module = self._safe_import(pkg)
            if module is None:
                continue
            if hasattr(module, "__path__"):
                roots.append(module)
        return roots

    def _import_admin_modules(self, roots: Iterable[ModuleType]) -> None:
        for root in roots:
            prefix = root.__name__ + "."
            for _, modname, _ in pkgutil.walk_packages(root.__path__, prefix):
                if modname.endswith(".admin") or ".admin." in modname:
                    self._safe_import(modname)

    def _import_named_modules(self, roots: Iterable[ModuleType], name: str) -> None:
        for root in roots:
            dotted = f"{root.__name__}.{name}"
            module = self._safe_import(dotted)
            if module is None:
                continue
            path = getattr(module, "__path__", None)
            if path is None:
                continue
            prefix = module.__name__ + "."
            for _, submodule, _ in pkgutil.walk_packages(path, prefix):
                self._safe_import(submodule)

    def _safe_import(self, module_name: str) -> ModuleType | None:
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if getattr(exc, "name", None) == module_name:
                self.logger.debug("Module %s not found during discovery", module_name)
                return None
            self.logger.exception("Failed to import module %s", module_name)
            return None
        except ImportError:
            self.logger.exception("Failed to import module %s", module_name)
            return None


# The End

