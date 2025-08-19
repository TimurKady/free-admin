# -*- coding: utf-8 -*-
"""Admin panel configuration for RBAC models."""

from contrib.admin.core.model import ModelAdmin
from contrib.admin.hub import admin_site

from ..models.rbac import AdminGroup, AdminGroupPermission, AdminUserPermission


class AdminGroupAdmin(ModelAdmin):
    """Admin configuration for :class:`AdminGroup`."""

    model = AdminGroup
    list_display = ("name", "description")


class AdminUserPermissionAdmin(ModelAdmin):
    """Admin configuration for :class:`AdminUserPermission`."""

    model = AdminUserPermission
    list_display = ("user", "content_type", "action")


class AdminGroupPermissionAdmin(ModelAdmin):
    """Admin configuration for :class:`AdminGroupPermission`."""

    model = AdminGroupPermission
    list_display = ("group", "content_type", "action")


admin_site.register(app="admin", model=AdminGroup, admin_cls=AdminGroupAdmin, settings=True)
admin_site.register(app="admin", model=AdminUserPermission, admin_cls=AdminUserPermissionAdmin, settings=True)
admin_site.register(app="admin", model=AdminGroupPermission, admin_cls=AdminGroupPermissionAdmin, settings=True)

# The End
