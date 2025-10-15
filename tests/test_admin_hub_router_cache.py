# -*- coding: utf-8 -*-
"""Tests covering AdminHub router cache invalidation logic."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from freeadmin.core.runtime.hub import AdminHub


def _build_hub(router: MagicMock | None = None) -> AdminHub:
    """Return a minimally initialised ``AdminHub`` for cache tests."""

    hub = object.__new__(AdminHub)
    hub._settings = MagicMock()
    hub.admin_site = MagicMock()
    hub.discovery = MagicMock()
    hub._app_configs = {}
    hub._started_configs = set()
    hub._router = router
    return hub  # type: ignore[return-value]


def test_autodiscover_invalidates_router_when_new_configured() -> None:
    """New discoveries should drop cached router wrappers."""

    aggregator = MagicMock()
    router = MagicMock()
    router.aggregator = aggregator
    hub = _build_hub(router)

    new_config = SimpleNamespace(import_path="example.pkg")
    hub.discovery.discover_all.return_value = [new_config]

    discovered = hub.autodiscover(["example"])

    assert discovered == [new_config]
    aggregator.invalidate_admin_router.assert_called_once_with()
    assert hub._app_configs["example.pkg"] is new_config
    assert hub._router is None


def test_autodiscover_preserves_router_for_existing_configs() -> None:
    """Discovering previously known configs must keep the cache intact."""

    aggregator = MagicMock()
    router = MagicMock()
    router.aggregator = aggregator
    existing = SimpleNamespace(import_path="example.pkg")
    hub = _build_hub(router)
    hub._app_configs = {existing.import_path: existing}

    duplicate_config = SimpleNamespace(import_path="example.pkg")
    hub.discovery.discover_all.return_value = [duplicate_config]

    discovered = hub.autodiscover(["example"])

    assert discovered == [duplicate_config]
    aggregator.invalidate_admin_router.assert_not_called()
    assert hub._router is router


@pytest.mark.parametrize("packages", [[], tuple()])
def test_autodiscover_no_packages_returns_empty(packages) -> None:
    """No discovery roots should lead to no router changes."""

    aggregator = MagicMock()
    router = MagicMock()
    router.aggregator = aggregator
    hub = _build_hub(router)

    discovered = hub.autodiscover(packages)

    assert discovered == []
    aggregator.invalidate_admin_router.assert_not_called()
    assert hub._router is router
