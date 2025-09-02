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
        return self.merge_readonly({
            "type": "string",
            "title": self.get_title(),
        })

# The End

