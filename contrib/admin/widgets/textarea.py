# -*- coding: utf-8 -*-
"""
textarea

Multi-line text input widget.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Dict

from .base import BaseWidget
from .registry import registry


@registry.register("textarea")
class TextAreaWidget(BaseWidget):
    assets_js = (
        "https://cdn.jsdelivr.net/npm/ace-builds@latest/src-noconflict/ace.min.js",
        "/static/widgets/textarea.js",
    )

    def get_schema(self) -> Dict[str, Any]:
        fd = self.ctx.field
        meta = getattr(fd, "meta", {}) or {}

        fmt = self.config.get("format", "textarea")
        schema: Dict[str, Any] = {
            "type": "string",
            "format": fmt,
            "title": self.get_title(),
        }

        options = dict(self.config.get("options", {}))

        syntax = meta.get("syntax")
        if syntax:
            theme = meta.get("ace_theme", "chrome")
            ace_opts = options.get("ace", {}).copy()
            ace_opts.update({"mode": syntax, "theme": theme})
            options["ace"] = ace_opts

        if options:
            schema["options"] = options

        schema.setdefault("options", {})
        schema["options"].setdefault("inputAttributes", {})
        schema["options"]["inputAttributes"]["data-textarea-autosize"] = "1"

        return self.merge_readonly(schema)

# The End

