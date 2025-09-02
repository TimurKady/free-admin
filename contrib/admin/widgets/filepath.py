# -*- coding: utf-8 -*-
"""
filepath

Widget for storing file path strings with upload support.


Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from pathlib import PurePosixPath
from typing import Any, Dict

from ..core.settings import SettingsKey, system_config

from .base import BaseWidget
from .registry import registry


@registry.register("filepath")
class FilePathWidget(BaseWidget):
    """Widget that represents uploaded file paths."""

    assets_js = ("/static/widgets/filepath.js",)
    upload_handler: str = "FilePathUploader"

    def get_schema(self) -> Dict[str, Any]:
        prefix = (self.ctx.prefix if self.ctx else "").rstrip("/")
        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm").strip("/")
        md = self.ctx.descriptor if self.ctx else None
        admin = self.ctx.admin if self.ctx else None

        app = (
            getattr(admin, "app_label", None)
            or getattr(md, "app", None)
            or getattr(md, "app_label", "")
        ).lower()
        name = (
            getattr(admin, "model_slug", None)
            or getattr(md, "name", None)
            or getattr(md, "model_name", "")
        ).lower()

        endpoint = str(PurePosixPath(prefix) / orm_prefix / app / name / "upload")

        schema = {
            "type": "string",
            "title": self.get_title(),
            "format": "url",
            "options": {"upload": {"upload_handler": self.upload_handler}},
            "links": [{"href": "{{self}}"}],
            "upload_endpoint": endpoint,
        }
        return self.merge_readonly(schema)

    def to_python(self, value: Any, options: Dict[str, Any] | None = None) -> str:
        if value in (None, ""):
            return ""
        return str(value)

    def to_storage(self, value: Any, options: Dict[str, Any] | None = None) -> str | None:
        if isinstance(value, str) and value:
            return str(PurePosixPath(value)).lstrip("/")
        return None

# The End

