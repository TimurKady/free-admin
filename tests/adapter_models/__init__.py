# -*- coding: utf-8 -*-
"""
adapter_models

Test helpers exposing adapter-backed models.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from types import SimpleNamespace

from freeadmin.apps.system import (
    AdminContentType,
    AdminGroup,
    AdminGroupPermission,
    AdminUser,
    AdminUserPermission,
    SystemSetting,
)


class AdapterModelsRegistry:
    """Expose adapter-backed models for tests and fixtures."""

    def __init__(self) -> None:
        """Bind adapter models into a convenient namespace."""

        self.models = SimpleNamespace(
            user=AdminUser,
            user_permission=AdminUserPermission,
            group=AdminGroup,
            group_permission=AdminGroupPermission,
            content_type=AdminContentType,
            system_setting=SystemSetting,
        )


registry = AdapterModelsRegistry()
models = registry.models

__all__ = ["registry", "models"]


# The End
