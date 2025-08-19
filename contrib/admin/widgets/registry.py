# -*- coding: utf-8 -*-
"""
Widget Registry Class.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from typing import Dict, Type, Tuple, Any
from .base import WidgetBase

class WidgetRegistry:
    def __init__(self) -> None:
        self._map: Dict[str, WidgetBase] = {}

    def register(self, cls: Type[WidgetBase]) -> Type[WidgetBase]:
        key = getattr(cls, "key", None)
        if not key or not isinstance(key, str):
            raise ValueError("Widget must define string 'key'")
        if key in self._map:
            raise ValueError(f"Widget '{key}' already registered")
        self._map[key] = cls()  # singletons OK
        return cls

    def get(self, key: str) -> WidgetBase:
        if key not in self._map:
            raise KeyError(f"Unknown widget '{key}'")
        return self._map[key]

    def items(self):
        return self._map.items()

registry = WidgetRegistry()

def register_widget(cls):
    return registry.register(cls)
