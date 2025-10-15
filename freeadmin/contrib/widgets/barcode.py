# -*- coding: utf-8 -*-
"""
Barcode widget for UUID fields

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from typing import Any, Dict
from uuid import UUID

from .base import BaseWidget
from .registry import registry

@registry.register("barcode")
class BarCodeWidget(BaseWidget):
    key = "barcode"

    default_options: Dict[str, Any] = {"format": "code128", "displayValue": True}

    def __init__(
        self, ctx: Any | None = None, *, options: Dict[str, Any] | None = None, **config: Any
    ) -> None:
        super().__init__(ctx, **config)
        self.options: Dict[str, Any] = {**self.default_options, **(options or {})}

    uuid_pattern = (
        r"^[0-9a-fA-F]{8}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{12}$"
    )

    class Meta:
        js = (
            "/static/vendors/jsbarcode/JsBarcode.all.min.js",
            "/static/widgets/barcode-editor.js",
        )

    def get_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {
            "type": "string",
            "title": self.get_title(),
            "pattern": self.uuid_pattern,
            "options": {
                "widget": "barcode",
                "show_input": False,
                "options": self.options,
            },
        }
        return self.merge_readonly(schema)

    def to_python(self, value: Any, options=None) -> Any:
        if value in (None, ""):
            return None
        try:
            UUID(str(value))
        except ValueError as exc:
            raise ValueError("Invalid UUID format") from exc
        return str(value)

    def to_storage(self, value: Any, options=None) -> Any:
        return self.to_python(value, options)

# The End

