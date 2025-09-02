# -*- coding: utf-8 -*-
"""
groups

RBAC: groups and permissions (flat model without a separate Permission entity).

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from ..boot import admin as boot_admin

AdminGroup = boot_admin.adapter.group_model
AdminGroupPermission = boot_admin.adapter.group_permission_model

__all__ = ["AdminGroup", "AdminGroupPermission"]

# The End

