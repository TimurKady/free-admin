# -*- coding: utf-8 -*-
"""
radio

Radio button widget.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from enum import Enum, EnumMeta
from typing import Any, Dict, Tuple, Iterable

from . import BaseWidget, register_widget

def _humanize(name: str) -> str:
    return name.replace("_", " ").title()

def _normalize_choices(choices) -> Tuple[list[Any], list[str]]:
    """
    Поддерживаем:
      - dict {value: label}
      - iterable из пар (value, label)
      - iterable из значений (value)
      - класс Enum (EnumMeta) или iterable из элементов Enum
    Возвращаем (enum_values, enum_titles).
    """
    if not choices:
        return [], []

    # Класс Enum
    if isinstance(choices, EnumMeta):
        vals, titles = [], []
        for m in choices:
            vals.append(m.value)
            lbl = getattr(m, "label", None) or getattr(m, "title", None) or _humanize(m.name)
            titles.append(str(lbl))
        return vals, titles

    # Словарь {value: label}
    if isinstance(choices, dict):
        vals, titles = [], []
        for k, v in choices.items():
            vals.append(k.value if isinstance(k, Enum) else k)
            if isinstance(v, Enum):
                lbl = getattr(v, "label", None) or getattr(v, "title", None) or _humanize(v.name)
            else:
                lbl = v
            titles.append(str(lbl))
        return vals, titles

    # Iterable of objects with ``const`` and ``title`` attributes
    # (e.g. :class:`contrib.admin.schema.descriptors.Choice` instances)
    if isinstance(choices, Iterable) and not isinstance(choices, (str, bytes)):
        choices_list = list(choices)
        if choices_list and all(hasattr(c, "const") and hasattr(c, "title") for c in choices_list):
            vals = [getattr(item, "const") for item in choices_list]
            titles = [str(getattr(item, "title")) for item in choices_list]
            return vals, titles
        # reuse ``choices_list`` in generic iterable processing below
        choices = choices_list

    # Итерируемое
    vals, titles = [], []
    for item in choices:
        # пара (value, label)
        if isinstance(item, tuple) and len(item) == 2:
            v, lbl = item
            vals.append(v.value if isinstance(v, Enum) else v)
            if isinstance(lbl, Enum):
                lbl = getattr(lbl, "label", None) or getattr(lbl, "title", None) or _humanize(lbl.name)
            titles.append(str(lbl))
        else:
            # одиночное значение (Enum или примитив)
            if isinstance(item, Enum):
                vals.append(item.value)
                lbl = getattr(item, "label", None) or getattr(item, "title", None) or _humanize(item.name)
                titles.append(str(lbl))
            else:
                vals.append(item)
                titles.append(str(item))
    return vals, titles

@register_widget("radio")
class RadioWidget(BaseWidget):
    """Радиокнопки для полей с choices (IntEnum/CharEnum и т.п.)."""

    def get_schema(self) -> Dict[str, Any]:
        fd = self.ctx.field

        enum_vals, titles = _normalize_choices(getattr(fd, "choices", None))

        # тип по факту значений (если все ints → integer, иначе string)
        typ = "integer" if enum_vals and all(isinstance(v, int) for v in enum_vals) else "string"

        return self.merge_readonly({
            "type": typ,
            "title":  self.get_title(),
            "format": "radio",
            "enum": enum_vals,                    # ← только значения
            "options": {"enum_titles": titles},   # ← подписи отдельно
        })

    def get_startval(self) -> Any:
        val = super().get_startval()  # берёт instance.<field> (см. BaseWidget)
        if val is None:
            return None
        raw = getattr(val, "value", val)  # Enum → его .value
        # Приведём тип симметрично схеме
        return int(raw) if isinstance(raw, bool) is False and isinstance(raw, (int,)) else (str(raw) if not isinstance(raw, int) else raw)

    def to_storage(self, value: Any, options: Dict[str, Any] | None = None) -> Any:
        return value

# The End
