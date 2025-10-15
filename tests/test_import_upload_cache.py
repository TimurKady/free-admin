# -*- coding: utf-8 -*-
"""
test_import_upload_cache

Validate ImportService persistence and cleanup using the SQLite upload cache.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import asyncio
import io
import json
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

ImportService = import_module("freeadmin.core.interface.services.import").ImportService


class DummyAdapter:
    """Adapter stub storing created objects in memory."""

    async def create(self, model, **row):
        """Persist ``row`` on ``model`` and return the created instance."""

        obj = model(**row)
        model._store.append(obj)
        return obj


class DummyModel(SimpleNamespace):
    """Simple namespace acting as backing storage container."""

    _store: list[SimpleNamespace] = []


class DummyAdmin(SimpleNamespace):
    """Minimal admin stub implementing import hooks."""

    def __init__(self, adapter: DummyAdapter) -> None:
        super().__init__()
        self.adapter = adapter
        self.model = DummyModel
        self.model._store = []
        self.last_row_keys: list[str] | None = None

    def get_import_fields(self) -> list[str]:
        """Return field names accepted by the importer."""

        return ["name", "value"]

    async def get_or_create_for_import(
        self, data: dict[str, object]
    ) -> tuple[SimpleNamespace, bool]:
        """Create or reuse an object matching ``data``."""

        self.last_row_keys = list(data.keys())
        for obj in self.model._store:
            if getattr(obj, "name", None) == data.get("name"):
                return obj, False
        created = await self.adapter.create(self.model, **data)
        return created, True

    async def update_for_import(
        self, obj: SimpleNamespace, data: dict[str, object]
    ) -> None:
        """Update ``obj`` with ``data`` fields."""

        self.last_row_keys = list(data.keys())
        for key, value in data.items():
            setattr(obj, key, value)


class TestImportServiceSQLiteCache:
    """Exercise ImportService behaviour with SQLite-backed cache."""

    @pytest.mark.asyncio
    async def test_preview_and_run_survive_restart(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "cache.sqlite3"
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        adapter = DummyAdapter()
        admin = DummyAdmin(adapter)
        service = ImportService(
            tmp_dir=str(upload_dir),
            cache_path=str(cache_path),
            ttl=5,
            cleanup_interval=1,
        )
        payload = [{"name": "alpha", "value": "1"}]
        upload = SimpleNamespace(
            filename="data.json", file=io.BytesIO(json.dumps(payload).encode("utf-8"))
        )
        token = await service.cache_upload(upload)
        preview = await service.preview(token, ["name", "value"])
        assert preview[0]["name"] == "alpha"
        restarted = ImportService(
            tmp_dir=str(upload_dir),
            cache_path=str(cache_path),
            ttl=5,
            cleanup_interval=1,
        )
        preview_after_restart = await restarted.preview(token, ["name", "value"])
        assert preview_after_restart[0]["value"] == "1"
        report = await restarted.run(admin, token, ["name", "value"])
        assert report.processed == 1
        await restarted.cleanup(token)
        assert list(upload_dir.iterdir()) == []

    @pytest.mark.asyncio
    async def test_parallel_upload_cleanup(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "cache.sqlite3"
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        adapter = DummyAdapter()
        admin = DummyAdmin(adapter)
        service = ImportService(
            tmp_dir=str(upload_dir),
            cache_path=str(cache_path),
            ttl=5,
            cleanup_interval=1,
        )

        async def handle_upload(index: int) -> list[dict[str, object]]:
            rows = [{"name": f"item-{index}", "value": str(index)}]
            upload = SimpleNamespace(
                filename=f"data{index}.json",
                file=io.BytesIO(json.dumps(rows).encode("utf-8")),
            )
            token = await service.cache_upload(upload)
            preview = await service.preview(token, ["name", "value"])
            assert preview[0]["name"] == f"item-{index}"
            report = await service.run(admin, token, ["name", "value"])
            assert report.processed == 1
            await service.cleanup(token)
            return preview

        previews = await asyncio.gather(*(handle_upload(i) for i in range(5)))
        assert len(previews) == 5
        assert list(upload_dir.iterdir()) == []


# The End

