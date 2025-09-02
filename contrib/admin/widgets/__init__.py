# -*- coding: utf-8 -*-
"""
__init__

Utilities for working with admin form widgets.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

# admin/widgets/__init__.py
from __future__ import annotations

from .base import BaseWidget
from .registry import registry

__all__ = ["BaseWidget", "registry"]

# Import built-in widgets so they register themselves:
from .text import TextWidget      # noqa: F401
from .textarea import TextAreaWidget  # noqa: F401
from .relations import RelationsWidget  # noqa: F401
from .number import NumberWidget  # noqa: F401
from .checkbox import CheckboxWidget  # noqa: F401
from .radio import RadioWidget          # noqa: F401
from .datetime import DateTimeWidget  # noqa: F401
from .select2 import Select2Widget  # noqa: F401
from .filepath import FilePathWidget  # noqa: F401

# The End

