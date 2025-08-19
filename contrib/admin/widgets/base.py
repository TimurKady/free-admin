# -*- coding: utf-8 -*-
"""
Base Widget Class.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""
from typing import Any, Dict, Iterable, Tuple
from fastapi import APIRouter

class WidgetBase:
    """
    Base class of the field widget.
    The contract is minimal: schema, ui, assets, endpoints, converters.
    """
  
    key: str = "base"  # системное имя виджета, например: 'text', 'integer', 'fk'

    # ---- Формирование формы ----
    def get_schema(self, field, options: Dict[str, Any]) -> Dict[str, Any]:
        """Фрагмент JSON Schema для поля (type/format/enum и т.п.)."""
        return {}

    def get_ui(self, field, options: Dict[str, Any]) -> Dict[str, Any]:
        """Фрагмент ui-конфига (uiSchema/опции рендеринга)."""
        return {}

    # ---- Ассеты и эндпоинты ----
    def assets(self) -> Dict[str, Iterable[str]]:
        """
        Возвращает словарь путей статических ресурсов:
        {"js": [...], "css": [...], "partials": [...]}
        """
        return {"js": [], "css": [], "partials": []}

    def endpoints(self, router: APIRouter) -> None:
        """
        Регистрирует эндпоинты виджета под /api/widgets/<key>/*.
        По умолчанию — ничего.
        """
        return None

    # ---- Конвертеры значений ----
    def format_value(self, value: Any, options: Dict[str, Any]) -> Any:
        """
        Приводит значение к «чистому» виду для шаблонов/рендера (строки, примитивы).
        Не меняет тип хранения, только для отображения.
        """
        return value

    def to_python(self, value: Any, options: Dict[str, Any]) -> Any:
        """
        Приводит из входного (обычно JSON/строка) к корректному Python-объекту.
        Используется до валидации/сохранения.
        """
        return value

    def to_storage(self, value: Any, options: Dict[str, Any]) -> Any:
        """
        Приводит Python-объект к формату БД/ORM (id, JSON, строка и т.п.).
        Вызывается перед записью в БД.
        """
        return value
