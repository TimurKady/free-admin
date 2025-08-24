# -*- coding: utf-8 -*-
"""
registry

Widget registry.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from typing import Dict, Type

from ..schema.descriptors import FieldDescriptor
from .base import BaseWidget


class WidgetRegistry:
    def __init__(self) -> None:
        self._by_key: Dict[str, Type[BaseWidget]] = {}

    def register(self, key: str):
        """Декоратор регистрации виджета по ключу."""
        def _decorator(cls: Type[BaseWidget]) -> Type[BaseWidget]:
            cls.key = key
            self._by_key[key] = cls
            return cls
        return _decorator

    def get(self, key: str) -> Type[BaseWidget] | None:
        return self._by_key.get(key)

    def resolve_for_field(self, fd: FieldDescriptor) -> str:
        """Маппинг поля → ключ виджета."""
        k = (fd.kind or "").lower()  # "string" | "int" | "bool" | "date" | "m2m" | "fk" | ...
    
        # 1) булевы — всегда чекбокс (даже если заданы choices типа Yes/No)
        if k in ("bool", "boolean"):
            return "checkbox"

        if fd.relation is not None:
            return "relation"

        if fd.choices is not None:
            return "radio"

        if k in ("int", "integer", "float", "number"):
            return "number"
        if k in ("date", "datetime", "time"):
            return "datetime"
        if k == "text":
            return "textarea"
        if k == "string":
            return "text"
        return "text"

registry = WidgetRegistry()

def register_widget(key: str):
    return registry.register(key)

# The End
