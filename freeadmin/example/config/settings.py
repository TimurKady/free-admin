# -*- coding: utf-8 -*-
"""
settings

Minimal configuration objects for the FreeAdmin example project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(slots=True)
class ExampleSettings:
    """Store runtime metadata for the FreeAdmin example project."""

    ADMIN_PATH: ClassVar[str] = "/panel"
    INSTALLED_APPS: ClassVar[list[str]] = ["freeadmin.example.apps.demo"]

    project_name: str = "FreeAdmin Example"
    session_secret: str = "change-me"

    def describe(self) -> dict[str, str]:
        """Return a mapping describing the active settings."""

        return {
            "project_name": self.project_name,
            "session_secret": self.session_secret,
            "admin_path": self.ADMIN_PATH,
            "installed_apps": ", ".join(self.INSTALLED_APPS),
        }


__all__ = ["ExampleSettings"]

# The End

