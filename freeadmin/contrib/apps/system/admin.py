# -*- coding: utf-8 -*-
"""
admin

Administrative configuration for built-in system models.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from freeadmin.core.models import ModelAdmin
from freeadmin.hub import admin_site
from freeadmin.widgets import Select2Widget

from freeadmin.boot import admin as boot_admin

AdminGroup = boot_admin.adapter.group_model
AdminGroupPermission = boot_admin.adapter.group_permission_model
AdminUser = boot_admin.adapter.user_model
AdminUserPermission = boot_admin.adapter.user_permission_model
SystemSetting = boot_admin.adapter.system_setting_model


class AdminGroupAdmin(ModelAdmin):
    """Admin configuration for :class:`AdminGroup`."""

    model = AdminGroup
    list_display = ("name", "description")


class AdminUserPermissionAdmin(ModelAdmin):
    """Admin configuration for :class:`AdminUserPermission`."""

    model = AdminUserPermission
    list_display = ("user", "content_type", "action")

    class Meta:
        """Widget overrides for AdminUserPermission admin form."""

        widgets = {
            "content_type": Select2Widget(),
        }


class AdminGroupPermissionAdmin(ModelAdmin):
    """Admin configuration for :class:`AdminGroupPermission`."""

    model = AdminGroupPermission
    list_display = ("group", "content_type", "action")


class AdminUserAdmin(ModelAdmin):
    """Admin configuration for :class:`AdminUser`."""

    model = AdminUser
    fields = ("username", "email", "is_staff", "is_superuser", "is_active")
    list_display = ("username", "email", "is_staff", "is_superuser", "is_active")
    list_filter = ("username", "email", "is_staff", "is_superuser", "is_active")


class SystemSettingAdmin(ModelAdmin):
    """Admin configuration for :class:`SystemSetting`."""

    model = SystemSetting
    label = "System Settings"
    label_singular = "System Setting"
    list_display = ("name", "key", "value")
    list_filter = ("name", "key", "value")
    fields = ("name", "key", "value", "value_type", "meta")

    class Meta:
        """Meta options for :class:`SystemSettingAdmin`."""

        pass


admin_site.register(app="admin", model=AdminGroup, admin_cls=AdminGroupAdmin, settings=True, icon="bi-people")
admin_site.register(app="admin", model=AdminUserPermission, admin_cls=AdminUserPermissionAdmin, settings=True, icon="bi-person-lock")
admin_site.register(app="admin", model=AdminGroupPermission, admin_cls=AdminGroupPermissionAdmin, settings=True, icon="bi-shield-lock")
admin_site.register(app="admin", model=AdminUser, admin_cls=AdminUserAdmin, settings=True, icon="bi-person")
admin_site.register(
    app="core",
    model=SystemSetting,
    admin_cls=SystemSettingAdmin,
    settings=True,
    icon="bi-gear",
)


# The End
