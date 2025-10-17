# -*- coding: utf-8 -*-
"""
icon

Shared utilities for the admin components.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from urllib.parse import urlparse


class IconPathMixin:
    """Provides helper to resolve icon paths."""

    @staticmethod
    def _resolve_icon_path(icon_path: str, prefix: str, static_segment: str) -> str:
        parsed = urlparse(icon_path)
        if parsed.scheme or icon_path.startswith("/"):
            return icon_path
        static_pos = icon_path.find("static/")
        if static_pos != -1:
            icon_path = icon_path[static_pos + len("static/") :]
        normalized_segment = str(static_segment or "").strip()
        if not normalized_segment:
            normalized_segment = "/staticfiles"
        if not normalized_segment.startswith("/"):
            normalized_segment = f"/{normalized_segment}"
        if len(normalized_segment) > 1 and normalized_segment.endswith("/"):
            normalized_segment = normalized_segment.rstrip("/")
        if normalized_segment == "/":
            base = "/"
        else:
            base = normalized_segment.rstrip("/")
        resolved_path = icon_path.lstrip("/")
        if not resolved_path:
            return base
        if base == "/":
            return f"/{resolved_path}"
        return f"{base}/{resolved_path}"

# The End

