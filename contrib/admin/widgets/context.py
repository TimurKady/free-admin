# -*- coding: utf-8 -*-
"""
context

Widget context helper.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from ..schema.descriptors import ModelDescriptor, FieldDescriptor

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from ..core.base import BaseModelAdmin  # тип для подсказок


@dataclass(frozen=True)
class WidgetContext:
    """Всё, что виджет должен знать о себе и окружении."""
    admin: BaseModelAdmin
    descriptor: ModelDescriptor           # описание модели (единый слой)
    field: FieldDescriptor                # описание поля (единый слой)
    name: str                             # имя поля в форме
    instance: Optional[Any]               # объект (None для add)
    mode: str                             # "add" | "edit" | "list"
    request: Any | None = None            # FastAPI Request (по необходимости)
    readonly: bool = False                # поле только для чтения?

# The End
