# -*- coding: utf-8 -*-
"""
__init__

Utilities for working with admin form widgets.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

# admin/widgets/__init__.py
from __future__ import annotations

from .base import BaseWidget
from .registry import registry
from .text import TextWidget
from .textarea import TextAreaWidget
from .relations import RelationsWidget
from .choices import ChoicesWidget
from .number import NumberWidget
from .checkbox import CheckboxWidget
from .radio import RadioWidget
from .datetime import DateTimeWidget
from .select2 import Select2Widget
from .filepath import FilePathWidget
from .barcode import BarCodeWidget

__all__ = [
    "BaseWidget",
    "registry",
    "TextWidget",
    "TextAreaWidget",
    "RelationsWidget",
    "ChoicesWidget",
    "NumberWidget",
    "CheckboxWidget",
    "RadioWidget",
    "DateTimeWidget",
    "Select2Widget",
    "FilePathWidget",
    "BarCodeWidget",
]

# The End

