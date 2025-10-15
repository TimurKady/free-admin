# -*- coding: utf-8 -*-
"""system_models

Shared access to built-in admin system models for tests.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Iterable

from freeadmin.contrib.apps.system import (
    AdminContentType,
    AdminGroup,
    AdminGroupPermission,
    AdminUser,
    AdminUserPermission,
    SystemSetting,
)


class SystemModels:
    """Provide convenient accessors for the built-in admin system models."""

    def __init__(self) -> None:
        """Create a namespace exposing all relevant admin system models."""

        self._models = SimpleNamespace(
            user=AdminUser,
            user_permission=AdminUserPermission,
            group=AdminGroup,
            group_permission=AdminGroupPermission,
            content_type=AdminContentType,
            system_setting=SystemSetting,
        )

    @property
    def models(self) -> SimpleNamespace:
        """Return the namespace of admin system models used across tests."""

        return self._models

    def module_names(self) -> set[str]:
        """Return module names that define the built-in admin system models."""

        return {
            model.__module__
            for model in self._iterate_models()
        }

    def _iterate_models(self) -> Iterable[type]:
        """Yield each model class held by the namespace."""

        return tuple(
            getattr(self._models, attribute)
            for attribute in vars(self._models)
        )


system_models = SystemModels()

__all__ = ["system_models", "SystemModels"]


# The End
