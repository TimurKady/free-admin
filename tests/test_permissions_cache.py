# -*- coding: utf-8 -*-
"""Tests covering SQLite-backed permission caching behaviour."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from freeadmin.contrib.adapters.tortoise.users import PermAction
from freeadmin.core.interface.services.admin import AdminService
from freeadmin.core.interface.services.permissions import PermissionsService


class CacheAdapter:
    """Adapter stub recording permission existence checks."""

    user_model = object()
    group_model = object()
    user_permission_model = object()
    group_permission_model = object()
    perm_action = PermAction

    def __init__(self, *, user_allowed: bool, group_allowed: bool = False) -> None:
        self.user_allowed = user_allowed
        self.group_allowed = group_allowed
        self.exists_calls: list[SimpleNamespace] = []

    def filter(self, model, **filters):
        return SimpleNamespace(model=model, filters=filters)

    async def exists(self, qs: SimpleNamespace) -> bool:
        self.exists_calls.append(qs)
        if qs.model is self.user_permission_model:
            return self.user_allowed
        return self.group_allowed

    def all(self, manager):  # pragma: no cover - patched in tests
        return manager

    async def fetch_values(self, qs, field: str, flat: bool = False):  # pragma: no cover
        return []


@pytest.mark.asyncio
async def test_permission_cache_hit(tmp_path) -> None:
    """Ensure cached results prevent repeated adapter calls."""

    adapter = CacheAdapter(user_allowed=True)
    service = PermissionsService(
        adapter,
        cache_path=str(tmp_path / "perm-cache.sqlite"),
        cache_ttl=timedelta(seconds=30),
    )
    service._get_group_ids = AsyncMock(return_value=[])
    user = SimpleNamespace(id=1, is_active=True, is_staff=True, is_superuser=False)

    allowed_first = await service._has_permission(user, PermAction.view, 101)
    assert allowed_first is True
    assert len(adapter.exists_calls) == 1

    allowed_second = await service._has_permission(user, PermAction.view, 101)
    assert allowed_second is True
    assert len(adapter.exists_calls) == 1


@pytest.mark.asyncio
async def test_permission_cache_ttl_expiry(tmp_path) -> None:
    """Ensure expired cache entries trigger a fresh adapter lookup."""

    adapter = CacheAdapter(user_allowed=True)
    service = PermissionsService(
        adapter,
        cache_path=str(tmp_path / "perm-cache.sqlite"),
        cache_ttl=timedelta(milliseconds=50),
    )
    service._get_group_ids = AsyncMock(return_value=[])
    user = SimpleNamespace(id=2, is_active=True, is_staff=True, is_superuser=False)

    await service._has_permission(user, PermAction.view, 202)
    adapter.user_allowed = False
    await asyncio.sleep(0.1)

    allowed_after_expiry = await service._has_permission(user, PermAction.view, 202)
    assert allowed_after_expiry is False
    assert len(adapter.exists_calls) >= 2


class DummyQuerySet:
    """Simple container exposing stored permission records."""

    def __init__(self, storage: dict[int, SimpleNamespace]) -> None:
        self.storage = storage


class DummyPermissionAdapter:
    """Adapter stub supporting AdminService permission operations."""

    perm_action = PermAction
    user_model = object()
    group_model = object()
    user_permission_model = type("UserPerm", (SimpleNamespace,), {})
    group_permission_model = type("GroupPerm", (SimpleNamespace,), {})
    DoesNotExist = KeyError
    IntegrityError = RuntimeError

    def __init__(self) -> None:
        self._descriptors: dict[type, SimpleNamespace] = {}

    def get_model_descriptor(self, model: type) -> SimpleNamespace:
        descriptor = self._descriptors.get(model)
        if descriptor is None:
            descriptor = SimpleNamespace(pk_attr="id", fields_map={}, fields=())
            self._descriptors[model] = descriptor
        return descriptor

    async def get(self, qs: DummyQuerySet, **filters):
        pk = filters.get("id")
        try:
            return qs.storage[int(pk)]
        except (KeyError, TypeError) as exc:
            raise self.DoesNotExist from exc


class DummyPermissionAdmin:
    """Minimal admin object persisting permission records in memory."""

    def __init__(self, model: type, adapter: DummyPermissionAdapter) -> None:
        self.model = model
        self.adapter = adapter
        self._records: dict[int, SimpleNamespace] = {}
        self._pk = 0

    def allow(self, user, action: str, obj) -> bool:
        return True

    def normalize_payload(self, payload: dict) -> dict:
        return dict(payload)

    def get_objects(self, request, user):
        return DummyQuerySet(self._records)

    async def create(self, request, user, md, payload: dict) -> SimpleNamespace:
        self._pk += 1
        record = SimpleNamespace(id=self._pk, **payload)
        self._records[self._pk] = record
        return record

    async def update(self, request, user, md, obj: SimpleNamespace, payload: dict) -> SimpleNamespace:
        for key, value in payload.items():
            setattr(obj, key, value)
        self._records[obj.id] = obj
        return obj

    async def delete(self, request, user, md, obj: SimpleNamespace) -> None:
        self._records.pop(obj.id, None)


class FakePermissionsService:
    """Expose async mocks for permission invalidation hooks."""

    def __init__(self) -> None:
        self.invalidate_user_permissions = AsyncMock()
        self.invalidate_group_permissions = AsyncMock()
        self._hooks: list = []

    def register_user_invalidation_hook(self, callback):
        """Store ``callback`` to match the real service API."""

        self._hooks.append(callback)

    def get_permission_snapshot(self) -> datetime:
        """Return a placeholder timestamp for compatibility."""

        return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_admin_service_triggers_permission_cache_invalidation(monkeypatch) -> None:
    """Ensure AdminService calls permission invalidation hooks on changes."""

    adapter = DummyPermissionAdapter()
    fake_service = FakePermissionsService()
    monkeypatch.setattr(
        "freeadmin.core.interface.services.admin.permissions_service",
        fake_service,
        raising=False,
    )

    user_admin = DummyPermissionAdmin(adapter.user_permission_model, adapter)
    user_service = AdminService(user_admin)
    request = SimpleNamespace()
    acting_user = SimpleNamespace()

    created = await user_service.create(
        request,
        acting_user,
        {"user_id": 10, "content_type_id": 1, "action": "view"},
    )
    assert created["ok"] is True
    fake_service.invalidate_user_permissions.assert_awaited_once_with(10)

    record_id = created["id"]
    fake_service.invalidate_user_permissions.reset_mock()
    await user_service.update(request, acting_user, record_id, {"user_id": 20})
    user_calls = {call.args[0] for call in fake_service.invalidate_user_permissions.await_args_list}
    assert user_calls == {10, 20}

    fake_service.invalidate_user_permissions.reset_mock()
    await user_service.delete(request, acting_user, record_id)
    delete_calls = [
        call.args[0] for call in fake_service.invalidate_user_permissions.await_args_list
    ]
    assert delete_calls == [20]

    group_admin = DummyPermissionAdmin(adapter.group_permission_model, adapter)
    group_service = AdminService(group_admin)
    fake_service.invalidate_group_permissions.reset_mock()
    created_group = await group_service.create(
        request,
        acting_user,
        {"group_id": 5, "content_type_id": 2, "action": "view"},
    )
    assert created_group["ok"] is True
    fake_service.invalidate_group_permissions.assert_awaited_once_with(5)

    group_id = created_group["id"]
    fake_service.invalidate_group_permissions.reset_mock()
    await group_service.update(request, acting_user, group_id, {"group_id": 7})
    group_calls = {
        call.args[0] for call in fake_service.invalidate_group_permissions.await_args_list
    }
    assert group_calls == {5, 7}

    fake_service.invalidate_group_permissions.reset_mock()
    await group_service.delete(request, acting_user, group_id)
    delete_group_calls = [
        call.args[0]
        for call in fake_service.invalidate_group_permissions.await_args_list
    ]
    assert delete_group_calls == [7]


# The End
