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
        return (
            f"{prefix.rstrip('/')}{static_segment.rstrip('/')}/"
            f"{icon_path.lstrip('/')}"
        )

# The End

