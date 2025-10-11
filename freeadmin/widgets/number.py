# -*- coding: utf-8 -*-
"""
number

Widget for numeric fields (integers and floats).

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Dict

from .base import BaseWidget
from .registry import registry


@registry.register("number")
class NumberWidget(BaseWidget):
    """Render numeric values using JSON Schema number/integer types."""

    def get_schema(self) -> Dict[str, Any]:
        kind = (getattr(self.ctx.field, "kind", "") or "").lower()
        schema_type = "integer" if kind in ("int", "integer") else "number"
        step_value = "1" if schema_type == "integer" else "0.1"
        return self.merge_readonly({
            "type": schema_type,
            "title": self.get_title(),
            "format": "number",
            "options": {
                "inputAttributes": {
                    "step": step_value,
                }
            },
        })

# The End
