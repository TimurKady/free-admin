# -*- coding: utf-8 -*-
"""
groups

RBAC: groups and permissions (flat model without a separate Permission entity).

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from tortoise import fields
from tortoise.models import Model

from .users import AdminUser, PermAction
from .content_type import AdminContentType


class AdminGroup(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=150, unique=True)
    description = fields.CharField(max_length=512, null=True)

    users: fields.ManyToManyRelation[AdminUser] = fields.ManyToManyField(
        "admin.AdminUser", related_name="groups", through="admin_user_groups"
    )

    class Meta:
        table = "admin_group"
        verbose_name = "Group"
        verbose_name_plural = "Groups"

    def __str__(self) -> str:
        return self.name


class AdminGroupPermission(Model):
    """Group permission on a model (or global, if content_type is NULL)."""

    id = fields.IntField(pk=True)
    group: fields.ForeignKeyRelation[AdminGroup] = fields.ForeignKeyField(
        "admin.AdminGroup", related_name="group_permissions", on_delete=fields.CASCADE
    )
    content_type: fields.ForeignKeyNullableRelation[AdminContentType] = fields.ForeignKeyField(
        "admin.AdminContentType", related_name="group_permissions", null=True, on_delete=fields.CASCADE
    )
    action = fields.CharEnumField(PermAction, index=True)

    class Meta:
        table = "admin_group_permissions"
        unique_together = (("group", "content_type", "action"),)
        indexes = (("group_id", "action", "content_type_id"),)
        verbose_name = "Group permissions"
        verbose_name_plural = "Group permissions"

    def __str__(self) -> str:
        ctd = self.content_type.dotted if self.content_type_id else "*"
        return f"{self.group_id}:{ctd}:{self.action}"

# The End

