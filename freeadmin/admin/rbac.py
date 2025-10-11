# -*- coding: utf-8 -*-
"""
rbac

Admin panel configuration for RBAC models.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from freeadmin.core.models import ModelAdmin
from freeadmin.hub import admin_site
from freeadmin.widgets import Select2Widget

from ..boot import admin as boot_admin
AdminGroup = boot_admin.adapter.group_model
AdminGroupPermission = boot_admin.adapter.group_permission_model
AdminUserPermission = boot_admin.adapter.user_permission_model


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


admin_site.register(app="admin", model=AdminGroup, admin_cls=AdminGroupAdmin, settings=True, icon="bi-people")
admin_site.register(app="admin", model=AdminUserPermission, admin_cls=AdminUserPermissionAdmin, settings=True, icon="bi-person-lock")
admin_site.register(app="admin", model=AdminGroupPermission, admin_cls=AdminGroupPermissionAdmin, settings=True, icon="bi-shield-lock")

# The End

