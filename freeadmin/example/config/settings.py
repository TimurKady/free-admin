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


@dataclass(slots=True)
class ExampleSettings:
    """Store runtime metadata for the FreeAdmin example project."""

    project_name: str = "FreeAdmin Example"
    session_secret: str = "change-me"

    def describe(self) -> dict[str, str]:
        """Return a mapping describing the active settings."""

        return {
            "project_name": self.project_name,
            "session_secret": self.session_secret,
        }


__all__ = ["ExampleSettings"]

# The End

