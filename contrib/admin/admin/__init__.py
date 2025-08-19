# -*- coding: utf-8 -*-
"""Admin registrations for admin models."""

from .user import AdminUserAdmin
from .rbac import (
    AdminGroupAdmin,
    AdminUserPermissionAdmin,
    AdminGroupPermissionAdmin,
)
from .setting import SystemSettingAdmin

__all__ = [
    "AdminUserAdmin",
    "AdminGroupAdmin",
    "AdminUserPermissionAdmin",
    "AdminGroupPermissionAdmin",
    "SystemSettingAdmin",
]

# The End
