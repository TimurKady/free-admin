# -*- coding: utf-8 -*-
"""
registry

Compatibility facade exposing boot registry utilities.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from ..core.boot.registry import (
    LOGGER,
    ModelModuleRegistry,
    ModelRegistrar,
    import_module,
)

__all__ = ["LOGGER", "ModelModuleRegistry", "ModelRegistrar", "import_module"]


# The End

