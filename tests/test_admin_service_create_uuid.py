# -*- coding: utf-8 -*-
"""
test_admin_service_create_uuid

Ensure AdminService.create returns UUID when model defines it.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import pytest
from fastapi import Request
from tortoise import Tortoise, fields, models
from uuid import uuid4

from freeadmin.core.models import ModelAdmin
from freeadmin.core.services.auth import AdminUserDTO
from freeadmin.core.services.admin import AdminService
from freeadmin.core.boot import admin as boot_admin


class Widget(models.Model):
    id = fields.IntField(pk=True)
    uuid = fields.UUIDField(default=uuid4, unique=True)
    name = fields.CharField(max_length=50)


class WidgetAdmin(ModelAdmin):
    model = Widget


class TestAdminServiceCreateUUID:
    """Verify that create returns both ID and UUID."""

    @pytest.mark.asyncio
    async def test_create_returns_uuid(self) -> None:
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": [__name__]})
        await Tortoise.generate_schemas()
        request = Request(scope={"type": "http", "headers": []})
        user = AdminUserDTO(id="1", username="tester")
        admin = WidgetAdmin(Widget, boot_admin)
        service = AdminService(admin)

        result = await service.create(request, user, {"name": "Gizmo"})
        assert "id" in result and "uuid" in result
        obj = await Widget.get(id=result["id"])
        assert str(obj.uuid) == str(result["uuid"])

        await Tortoise.close_connections()


# The End
