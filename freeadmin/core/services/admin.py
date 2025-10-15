# -*- coding: utf-8 -*-
"""
admin

Compatibility bridge exposing admin services from the interface layer.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import sys

from freeadmin.core.interface.services import admin as _admin_module

sys.modules[__name__] = _admin_module


# The End


# The End

