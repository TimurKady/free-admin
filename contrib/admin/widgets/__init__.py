# -*- coding: utf-8 -*-

"""Utilities for working with admin form widgets.

This module maintains a registry of widget classes so that they can be
referenced by a simple string key.  It also provides a minimal base class
that concrete widgets can extend.
"""

from __future__ import annotations
from typing import Any, Dict, Type


__all__ = [
    "BaseWidget",
    "register_widget",
    "get_widget",
    "FileUploadWidget",
    "SelectWidget",
    "TextWidget",
]

_registry: Dict[str, Type["BaseWidget"]] = {}


class BaseWidget:
    """Base class for form widgets used in the admin interface."""

    key: str = "base"

    def __init__(self, **options: Any) -> None:
        """Store widget configuration options."""
        self.options = options


def register_widget(key: str):
    """Decorator to register a widget class under ``key``."""

    def _decorator(cls: Type[BaseWidget]) -> Type[BaseWidget]:
        """Assign the registry key and store the widget class."""
        cls.key = key
        _registry[key] = cls
        return cls

    return _decorator


def get_widget(key: str) -> Type[BaseWidget] | None:
    """Return a registered widget class for ``key`` if it exists."""
    return _registry.get(key)


from .file import FileUploadWidget  # noqa: E402
from .select import SelectWidget  # noqa: E402
from .text import TextWidget  # noqa: E402


# The End
