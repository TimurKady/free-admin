# -*- coding: utf-8 -*-
"""
models

Adapter-backed model aliases for the system application.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from ....core.boot import admin as boot_admin

AdminUser = boot_admin.adapter.user_model
AdminUserPermission = boot_admin.adapter.user_permission_model
AdminGroup = boot_admin.adapter.group_model
AdminGroupPermission = boot_admin.adapter.group_permission_model
AdminContentType = boot_admin.adapter.content_type_model
SystemSetting = boot_admin.adapter.system_setting_model
PermAction = boot_admin.adapter.perm_action
SettingValueType = boot_admin.adapter.setting_value_type

__all__ = [
    "AdminUser",
    "AdminUserPermission",
    "AdminGroup",
    "AdminGroupPermission",
    "AdminContentType",
    "SystemSetting",
    "PermAction",
    "SettingValueType",
]


# The End
