# -*- coding: utf-8 -*-
"""
user_menu

Builtin user menu items.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from ..core.site import AdminSite
from ..core.settings import SettingsKey, system_config


class BuiltinUserMenuRegistrar:
    def __init__(self) -> None:
        self.logout_path = system_config.get_cached(SettingsKey.LOGOUT_PATH, "/logout")

    def register(self, site: AdminSite) -> None:
        site.register_user_menu(
            title="Logout",
            path=self.logout_path,
            icon="bi-box-arrow-right",
        )


# The End

