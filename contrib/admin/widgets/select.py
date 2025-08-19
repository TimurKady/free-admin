# -*- coding: utf-8 -*-
"""
Placeholder implementation for a selection widget.

Version: 1.0.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from . import BaseWidget, register_widget


@register_widget("select")
class SelectWidget(BaseWidget):
    """Placeholder widget for selecting values.

    Real initialisation (json-editor + BS5 + endpoints) will be added at the
    forms step.
    """

    pass


# The End
