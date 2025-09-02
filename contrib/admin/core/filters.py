# -*- coding: utf-8 -*-
"""
filters

Filter specification for admin queries.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FilterSpec:
    """Represent a single filter condition."""

    field: str
    op: str
    value: Any

    def lookup(self) -> str:
        """Return ORM lookup path using ``__`` separator."""
        return self.field.replace(".", "__")


__all__ = ["FilterSpec"]


# The End

