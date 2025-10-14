# -*- coding: utf-8 -*-
"""Tests ensuring system configuration startup is resilient to DB errors."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

import pytest
from tortoise.exceptions import OperationalError

from freeadmin.core.settings import config as config_module


class _AdapterTransaction:
    def __init__(self, adapter: "FailingAdapter") -> None:
        self._adapter = adapter

    async def __aenter__(self) -> "FailingAdapter":
        return self._adapter

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FailingAdapter:
    """Adapter that raises the configured ``error`` for every DB operation."""

    def __init__(self, error: BaseException) -> None:
        self.error = error

    def in_transaction(self) -> _AdapterTransaction:
        return _AdapterTransaction(self)

    async def get_or_none(self, *args: Any, **kwargs: Any) -> Any:
        raise self.error

    async def exists(self, *args: Any, **kwargs: Any) -> bool:
        raise self.error

    async def delete(self, *args: Any, **kwargs: Any) -> None:
        raise self.error

    async def save(self, *args: Any, **kwargs: Any) -> None:
        raise self.error

    async def create(self, *args: Any, **kwargs: Any) -> Any:
        raise self.error

    def filter(self, *args: Any, **kwargs: Any) -> Any:
        return SimpleNamespace()

    def all(self, *args: Any, **kwargs: Any) -> Any:
        raise self.error

    def values(self, *args: Any, **kwargs: Any) -> Any:
        raise self.error

    async def fetch_all(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise self.error


@pytest.mark.asyncio
async def test_ensure_seed_handles_operational_error(monkeypatch, caplog) -> None:
    config = config_module.SystemConfig()
    error = OperationalError("missing table system_settings")
    adapter = FailingAdapter(error)
    monkeypatch.setattr(
        config_module.SystemConfig, "adapter", property(lambda self: adapter)
    )

    caplog.set_level(logging.WARNING, logger=config_module.logger.name)

    await config.ensure_seed()

    assert "Skipping system configuration seed" in caplog.text
    assert "Run your migrations before starting FreeAdmin." in caplog.text


@pytest.mark.asyncio
async def test_reload_handles_operational_error(monkeypatch, caplog) -> None:
    config = config_module.SystemConfig()
    error = OperationalError("missing table system_settings")
    adapter = FailingAdapter(error)
    monkeypatch.setattr(
        config_module.SystemConfig, "adapter", property(lambda self: adapter)
    )

    caplog.set_level(logging.WARNING, logger=config_module.logger.name)

    await config.reload()

    assert "Skipping system configuration reload" in caplog.text
    assert "Run your migrations before starting FreeAdmin." in caplog.text


# The End
