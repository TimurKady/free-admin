# -*- coding: utf-8 -*-
"""
inline

Inline model admin definitions.
Inline Admin docs: contrib/admin/docs/INLINES.md

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from typing import Any, Type, Literal

from .base import BaseModelAdmin


class InlineModelAdmin(BaseModelAdmin):
    """Base class for building an inline model."""

    model: Type[Any]
    parent_fk_name: str
    can_delete: bool = True
    display: Literal["tabular", "stacked"] = "tabular"
    collapsed: bool = True


# The End

