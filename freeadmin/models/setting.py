# -*- coding: utf-8 -*-
"""
setting

System settings stored in the database.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from ..boot import admin as boot_admin

SettingValueType = boot_admin.adapter.setting_value_type
SystemSetting = boot_admin.adapter.system_setting_model

__all__ = ["SettingValueType", "SystemSetting"]

# The End

