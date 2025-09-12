# -*- coding: utf-8 -*-
"""
text

Placeholder implementation for a text input widget.

Version: 0.1.0
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
        fmt = self.config.get("format")
        if fmt is None and self.ctx is not None:
            kind = (getattr(self.ctx.field, "kind", "") or "").lower()
            if kind in ("int", "integer"):
                fmt = "number"
        if fmt is None:
            fmt = "text"
        schema: Dict[str, Any] = {
            "type": "string",
            "format": fmt,
            "title": self.get_title(),
        }
        return self.merge_readonly(schema)

# The End

