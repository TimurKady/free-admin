# -*- coding: utf-8 -*-
"""
views

Free Page Builder.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from ..core.site import AdminSite
from ..core.settings import SettingsKey, system_config


class BuiltinPagesRegistrar:
    def __init__(self) -> None:
        self.views_prefix = system_config.get_cached(SettingsKey.VIEWS_PREFIX, "/views")
        self.views_title = system_config.get_cached(SettingsKey.VIEWS_PAGE_TITLE, "Views")
        self.views_icon = system_config.get_cached(SettingsKey.VIEWS_PAGE_ICON, "bi-eye")
        self.orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")
        self.orm_title = system_config.get_cached(SettingsKey.ORM_PAGE_TITLE, "ORM")
        self.orm_icon = system_config.get_cached(SettingsKey.ORM_PAGE_ICON, "bi-diagram-3")
        self.settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        self.settings_title = system_config.get_cached(SettingsKey.SETTINGS_PAGE_TITLE, "Settings")
        self.settings_icon = system_config.get_cached(SettingsKey.SETTINGS_PAGE_ICON, "bi-gear")

    def register(self, site: AdminSite) -> None:
        @site.register_view(
            path=self.views_prefix,
            name=self.views_title,
            icon=self.views_icon,
            include_in_sidebar=False,
        )
        async def views_placeholder(request, user):
            page_title = await system_config.get(SettingsKey.VIEWS_PAGE_TITLE)
            return site.build_template_ctx(request, user, page_title=page_title)

        @site.register_view(
            path=self.orm_prefix,
            name=self.orm_title,
            icon=self.orm_icon,
            include_in_sidebar=False,
        )
        async def orm_home(request, user):
            page_title = await system_config.get(SettingsKey.ORM_PAGE_TITLE)
            return site.build_template_ctx(request, user, page_title=page_title, is_settings=False)

        @site.register_settings(path=self.settings_prefix, name=self.settings_title, icon=self.settings_icon)
        async def settings_home(request, user):
            page_title = await system_config.get(SettingsKey.SETTINGS_PAGE_TITLE)
            return site.build_template_ctx(request, user, page_title=page_title, is_settings=True)

# The End

