# -*- coding: utf-8 -*-
"""Tests covering SQLite-backed main menu caching behaviour."""

import types
from pathlib import Path

import pytest

from freeadmin.core.registry import PageRegistry
from freeadmin.core.menu import MenuBuilder
from freeadmin.core.cache.menu import MainMenuCache
from freeadmin.core.settings import SettingsKey, system_config


class _DummyAdmin:
    """Minimal stand-in for admin class references."""

    pass


class MenuCacheHarness:
    """Helper wiring together registry, builder, and cache for tests."""

    def __init__(self, tmp_path: Path) -> None:
        self.cache = MainMenuCache(path=str(tmp_path / "menu-cache.sqlite"))
        self.registry = PageRegistry()
        self.builder = MenuBuilder(self.registry, cache=self.cache)


def test_main_menu_cache_hit(tmp_path: Path) -> None:
    """Ensure cached payloads are reused when registry state is unchanged."""

    harness = MenuCacheHarness(tmp_path)
    harness.registry.register_view_entry(app="demo", model="alpha", admin_cls=_DummyAdmin)

    first_menu = harness.builder.build_main_menu(locale="en")
    assert first_menu, "expected menu entries after initial build"

    def _raise_iter(self):
        raise AssertionError("cache miss")

    harness.registry.iter_orm = types.MethodType(_raise_iter, harness.registry)
    harness.registry.iter_settings = types.MethodType(_raise_iter, harness.registry)

    second_menu = harness.builder.build_main_menu(locale="en")
    assert second_menu == first_menu


def test_main_menu_cache_locale_separation(tmp_path: Path) -> None:
    """Ensure different locales maintain distinct cache entries."""

    harness = MenuCacheHarness(tmp_path)
    harness.registry.register_view_entry(app="demo", model="bravo", admin_cls=_DummyAdmin)

    harness.builder.build_main_menu(locale="en-US")

    original_iter_orm = harness.registry.iter_orm
    original_iter_settings = harness.registry.iter_settings

    def _raise_iter(self):
        raise AssertionError("expected cache miss for new locale")

    harness.registry.iter_orm = types.MethodType(_raise_iter, harness.registry)
    harness.registry.iter_settings = types.MethodType(_raise_iter, harness.registry)

    with pytest.raises(AssertionError):
        harness.builder.build_main_menu(locale="fr-FR")

    harness.registry.iter_orm = original_iter_orm
    harness.registry.iter_settings = original_iter_settings
    harness.builder.build_main_menu(locale="fr-FR")

    harness.registry.iter_orm = types.MethodType(_raise_iter, harness.registry)
    harness.registry.iter_settings = types.MethodType(_raise_iter, harness.registry)
    assert harness.builder.build_main_menu(locale="fr-FR")
    assert harness.builder.build_main_menu(locale="en-US")


def test_main_menu_cache_invalidation(tmp_path: Path) -> None:
    """Ensure invalidation clears caches and rebuilds include new entries."""

    harness = MenuCacheHarness(tmp_path)
    harness.registry.register_view_entry(app="demo", model="charlie", admin_cls=_DummyAdmin)
    first = harness.builder.build_main_menu(locale="en")
    assert len(first) == 1
    assert harness.cache.items(), "expected cached payload after initial build"

    harness.registry.register_view_entry(app="demo", model="delta", admin_cls=_DummyAdmin)
    harness.builder.invalidate_main_menu()
    assert harness.cache.items() == []

    rebuilt = harness.builder.build_main_menu(locale="en")
    assert len(rebuilt) == 2

    def _raise_iter(self):
        raise AssertionError("cache should serve rebuilt menu")

    harness.registry.iter_orm = types.MethodType(_raise_iter, harness.registry)
    harness.registry.iter_settings = types.MethodType(_raise_iter, harness.registry)
    assert harness.builder.build_main_menu(locale="en") == rebuilt


def test_main_menu_cache_reflects_settings_changes(tmp_path: Path) -> None:
    """Changing system settings should result in new cache entries."""

    harness = MenuCacheHarness(tmp_path)
    harness.registry.register_view_entry(app="demo", model="echo", admin_cls=_DummyAdmin)

    original_menu = harness.builder.build_main_menu(locale="en")
    assert original_menu, "expected menu entries after initial build"
    assert original_menu[0].path.startswith("/orm/"), "expected default ORM prefix"

    key = SettingsKey.ORM_PREFIX.value
    original_prefix = system_config._cache.get(key, "/orm")  # type: ignore[attr-defined]
    had_key = key in system_config._cache  # type: ignore[attr-defined]

    original_iter_orm = harness.registry.iter_orm
    original_iter_settings = harness.registry.iter_settings

    try:
        system_config._cache[key] = "/orm-updated"  # type: ignore[attr-defined]

        def _raise_iter(self):
            raise AssertionError("expected cache miss after settings change")

        harness.registry.iter_orm = types.MethodType(_raise_iter, harness.registry)
        harness.registry.iter_settings = types.MethodType(_raise_iter, harness.registry)

        with pytest.raises(AssertionError):
            harness.builder.build_main_menu(locale="en")

        harness.registry.iter_orm = original_iter_orm
        harness.registry.iter_settings = original_iter_settings

        rebuilt_menu = harness.builder.build_main_menu(locale="en")
        assert rebuilt_menu[0].path.startswith("/orm-updated/"), "expected new prefix"

        harness.registry.iter_orm = types.MethodType(_raise_iter, harness.registry)
        harness.registry.iter_settings = types.MethodType(_raise_iter, harness.registry)
        assert harness.builder.build_main_menu(locale="en") == rebuilt_menu
    finally:
        if had_key:
            system_config._cache[key] = original_prefix  # type: ignore[attr-defined]
        else:
            system_config._cache.pop(key, None)  # type: ignore[attr-defined]
        harness.registry.iter_orm = original_iter_orm
        harness.registry.iter_settings = original_iter_settings


# The End

