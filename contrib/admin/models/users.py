# -*- coding: utf-8 -*-
"""
users

Admin user models.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from ..boot import admin as boot_admin

AdminUser = boot_admin.adapter.user_model
AdminUserPermission = boot_admin.adapter.user_permission_model
PermAction = boot_admin.adapter.perm_action

__all__ = ["AdminUser", "AdminUserPermission", "PermAction"]

# The End

