# -*- coding: utf-8 -*-
"""
ORM

Illustrative ORM configuration for the FreeAdmin example project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping

from freeadmin.orm import ORMConfig, ORMLifecycle


class ExampleORMConfig(ORMConfig):
    """Provide adapter wiring for the FreeAdmin example project."""

    def __init__(
        self,
        *,
        adapter_name: str = "tortoise",
        dsn: str | None = None,
        modules: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        """Store adapter metadata and declare project-specific modules."""

        project_modules = self._build_project_modules(modules)
        super().__init__(
            adapter_name=adapter_name,
            dsn=dsn,
            modules=project_modules,
        )

    def _build_project_modules(
        self, modules: Mapping[str, Iterable[str]] | None
    ) -> Dict[str, List[str]]:
        default_modules: Dict[str, List[str]] = {
            "models": ["example.apps.demo.models"],
        }
        if modules is None:
            return default_modules
        project_modules: Dict[str, List[str]] = {
            label: [str(value) for value in values]
            for label, values in modules.items()
        }
        for label, values in default_modules.items():
            bucket = project_modules.setdefault(label, [])
            for module in values:
                if module not in bucket:
                    bucket.append(module)
        return project_modules


__all__ = ["ExampleORMConfig", "ORMLifecycle"]

# The End

