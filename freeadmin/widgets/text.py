# -*- coding: utf-8 -*-
"""
text

Placeholder implementation for a text input widget.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from typing import Any, Dict
from .base import BaseWidget
from .registry import registry


@registry.register("text")
class TextWidget(BaseWidget):
    def get_schema(self) -> Dict[str, Any]:
        """Build a JSON Schema representation for the widget."""
        fmt = self.config.get("format")
        type_ = "string"
        kind = ""
        if self.ctx is not None:
            kind = (getattr(self.ctx.field, "kind", "") or "").lower()
            if kind in ("int", "integer"):
                type_ = "integer"
            elif kind in ("float", "double", "decimal", "number"):
                type_ = "number"
        if fmt is None:
            if kind in ("int", "integer"):
                fmt = "number"
            else:
                fmt = "text"
        schema: Dict[str, Any] = {
            "type": type_,
            "format": fmt,
            "title": self.get_title(),
        }
        return self.merge_readonly(schema)

# The End

