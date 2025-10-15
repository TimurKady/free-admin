# -*- coding: utf-8 -*-
"""
permissions

Compatibility bridge exposing permission services from the interface layer.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from ..interface.services.permissions import (
    PermAction,
    PermissionsService,
    permissions_service,
)

__all__ = ["PermAction", "PermissionsService", "permissions_service"]


# The End

