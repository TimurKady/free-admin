# -*- coding: utf-8 -*-
"""
base

Base widget class.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

# admin/widgets/base.py
from __future__ import annotations
from typing import Any, Dict
from abc import ABC, abstractmethod
from .context import WidgetContext


class BaseWidget(ABC):
    """
    Base Widget Class

    Widgets provide JSON Schema fragments and optional start values.
    """
    key: str = "base"

    def __init__(self, ctx: WidgetContext) -> None:
        self.ctx = ctx

    def get_title(self) -> str:
        label = getattr(self.ctx.field, "label", None)
        if label:
            return label
        name = self.ctx.name.replace("_", "\u00A0")
        return name[:1].upper() + name[1:]

    # === Формирование схем ===
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """JSON Schema-фрагмент для конкретного поля."""
        raise NotImplementedError

    def merge_readonly(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Вставить флаг ``readonly`` в схему при необходимости."""
        if self.ctx.readonly:
            schema["readonly"] = True
        return schema
    
    def get_startval(self) -> Any:
        """Стартовое значение для формы (edit) — по умолчанию из instance."""
        if self.ctx.instance is not None:
            return getattr(self.ctx.instance, self.ctx.name, None)
        return None

    async def prefetch(self) -> None:
        """Заготовка для асинхронной подготовки данных перед генерацией схемы."""
        return None

    # === Конвертеры значений ===
    def to_python(self, value: Any, options: Dict[str, Any] | None = None) -> Any:
        return value

    def to_storage(self, value: Any, options: Dict[str, Any] | None = None) -> Any:
        return value

# The End
