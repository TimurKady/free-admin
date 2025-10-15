# -*- coding: utf-8 -*-
"""
Test export selected action.

Verify that only chosen records are exported when using the action.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from tortoise import Tortoise, fields, models

from freeadmin.core.models import ModelAdmin
from freeadmin.core.boot import admin as boot_admin
from freeadmin.core.services.permissions import PermAction
from freeadmin.core.services.export import (
    ExportService,
    MemoryCacheBackend,
    SQLiteExportCacheBackend,
)
from freeadmin.core.actions.export_selected import ExportSelectedAction
from freeadmin.contrib.apps.system.api.views import (
    AdminAPIConfiguration,
    AdminActionsListView,
)
from fastapi import HTTPException, Request
import pytest
from tests.system_models import system_models


class Item(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)
    description = fields.CharField(max_length=100, null=True)


class ItemAdmin(ModelAdmin):
    model = Item
    export_fields = ("id", "name")


class DummySite:
    """Minimal admin site for API tests."""

    def __init__(self, admin):
        self._admin = admin

    def find_admin_or_404(self, app, model):  # pragma: no cover - simple stub
        return self._admin


class TestExportSelectedAction:
    @classmethod
    def setup_class(cls) -> None:
        asyncio.run(
            Tortoise.init(
                db_url="sqlite://:memory:",
                modules={
                    "models": [__name__],
                    "admin": list(system_models.module_names()),
                },
            )
        )
        asyncio.run(Tortoise.generate_schemas())
        cls.admin = ItemAdmin(Item, boot_admin.adapter)
        cls.user = SimpleNamespace(is_superuser=False, permissions={PermAction.export})

    @classmethod
    def teardown_class(cls) -> None:
        asyncio.run(Tortoise.close_connections())

    def test_action_exports_chosen_records(self) -> None:
        ExportSelectedAction.cache_backend = MemoryCacheBackend()

        async def _prepare() -> tuple[int, int, int]:
            await Item.all().delete()
            a = await Item.create(name="a")
            b = await Item.create(name="b")
            c = await Item.create(name="c")
            return a.id, b.id, c.id

        first, second, third = asyncio.run(_prepare())
        qs = self.admin.adapter.filter(Item, id__in=[first, third])
        params = {"fields": ["id", "name"], "fmt": "json"}
        result = asyncio.run(
            self.admin.perform_action("export_selected", qs, params, self.user)
        )
        token = result.report
        service = ExportService(
            self.admin.adapter, cache_backend=ExportSelectedAction.cache_backend
        )
        info = service.get_file(token)
        with info.path.open("r", encoding="utf-8") as fh:
            rows = json.load(fh)
        ids = {row["id"] for row in rows}
        assert ids == {first, third}
        assert info.filename.startswith("item_")

    def test_export_token_survives_new_service_instance(self) -> None:
        async def _prepare() -> int:
            await Item.all().delete()
            obj = await Item.create(name="persistent")
            return obj.id

        with tempfile.TemporaryDirectory() as tmp_dir:
            export_path = Path(tmp_dir) / "exports"
            export_path.mkdir(parents=True, exist_ok=True)
            db_path = Path(tmp_dir) / "export-cache.sqlite3"
            backend = SQLiteExportCacheBackend(path=str(db_path))
            ExportSelectedAction.cache_backend = backend
            item_id = asyncio.run(_prepare())
            queryset = self.admin.adapter.filter(Item, id__in=[item_id])
            params = {"fields": ["id", "name"], "fmt": "json"}
            service = ExportService(
                self.admin.adapter,
                tmp_dir=str(export_path),
                cache_backend=backend,
            )
            token = asyncio.run(
                service.run(
                    queryset,
                    params["fields"],
                    params["fmt"],
                    model_name=self.admin.model.__name__,
                )
            )
            restored_service = ExportService(
                self.admin.adapter,
                tmp_dir=str(export_path),
                cache_backend=SQLiteExportCacheBackend(path=str(db_path)),
            )
            info = restored_service.get_file(token)
            assert info.path.exists()
            assert info.filename.endswith(".json")
            restored_service.cleanup(token)

    def test_sqlite_backend_prunes_expired_tokens(self) -> None:
        async def _prepare() -> int:
            await Item.all().delete()
            obj = await Item.create(name="expired")
            return obj.id

        with tempfile.TemporaryDirectory() as tmp_dir:
            export_dir = Path(tmp_dir) / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            backend = SQLiteExportCacheBackend(
                path=str(Path(tmp_dir) / "export-cache.sqlite3")
            )
            ExportSelectedAction.cache_backend = backend
            item_id = asyncio.run(_prepare())
            queryset = self.admin.adapter.filter(Item, id__in=[item_id])
            params = {"fields": ["id", "name"], "fmt": "json"}
            service = ExportService(
                self.admin.adapter,
                tmp_dir=str(export_dir),
                ttl=1,
                cache_backend=backend,
            )
            token = asyncio.run(
                service.run(
                    queryset,
                    params["fields"],
                    params["fmt"],
                    model_name=self.admin.model.__name__,
                )
            )
            time.sleep(1.5)
            with pytest.raises(HTTPException):
                service.get_file(token)
            assert token not in {key for key, _ in backend.items()}

    def test_actions_endpoint_excludes_legacy_action(self) -> None:
        site = DummySite(self.admin)
        config = AdminAPIConfiguration()
        view = AdminActionsListView(config)
        scope = {
            "type": "http",
            "app": SimpleNamespace(state=SimpleNamespace(admin_site=site)),
            "headers": [],
        }

        async def receive() -> dict[str, str]:
            return {"type": "http.request"}

        request = Request(scope, receive)
        data = asyncio.run(
            view.get(request, app="app", model="item", user=self.user)
        )
        names = {d["name"] for d in data}
        assert "export_selected_wizard" in names
        assert "export_selected" not in names


# The End

