# -*- coding: utf-8 -*-
"""
test_example_application

Smoke tests that validate the example application setup.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from example.config.main import ExampleApplication
from example.config.orm import (
    ADMIN_APP_MODULES,
    MODELS_APP_MODULES,
    SYSTEM_APP_MODULES,
    ExampleORMConfig,
)
from tests.sampleapp.app import default as sample_app_config
from tortoise import Tortoise

from freeadmin.adapters.tortoise.adapter import Adapter as TortoiseAdapter
from freeadmin.orm import ORMConfig


class TestExampleApplicationSmoke:
    """Verify that the example application mounts the admin router."""

    def test_admin_router_mounted(self) -> None:
        """Ensure configuring the example attaches the admin site to the app."""

        application = ExampleApplication()
        app = application.configure()

        assert getattr(app.state, "admin_site", None) is not None


class TestExampleApplicationStartup:
    """Ensure application configs execute startup hooks during boot."""

    @pytest.mark.asyncio
    async def test_app_config_startup_called(self) -> None:
        """Verify AppConfig.startup executes when FastAPI starts up."""

        sample_app_config.ready_calls = 0
        application = ExampleApplication()
        application.register_packages(["tests.sampleapp"])
        app = application.configure()

        boot_manager = application.boot_manager
        hub = boot_manager._ensure_hub()
        hub.admin_site.finalize = AsyncMock()
        hub.admin_site.cards.start_publishers = AsyncMock()
        hub.admin_site.cards.shutdown_publishers = AsyncMock()
        boot_manager._config = SimpleNamespace(
            ensure_seed=AsyncMock(),
            reload=AsyncMock(),
        )

        await app.router.startup()
        try:
            assert sample_app_config.ready_calls == 1
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_app_initialises_orm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify the example app initialises and tears down Tortoise ORM."""

        init_arguments: dict[str, object] = {}
        shutdown_calls: list[bool] = []

        async def fake_init(*, config: dict[str, object]) -> None:
            init_arguments["config"] = config

        async def fake_close() -> None:
            shutdown_calls.append(True)

        monkeypatch.setattr(Tortoise, "init", fake_init)
        monkeypatch.setattr(Tortoise, "close_connections", fake_close)

        custom_dsn = "sqlite:///example.db"
        custom_config = deepcopy(ExampleORMConfig.config)
        custom_config["connections"][ExampleORMConfig.default_connection_name] = custom_dsn
        orm_config = ORMConfig.build(
            adapter_name=ExampleORMConfig.adapter_name,
            config=custom_config,
        )
        application = ExampleApplication(orm=orm_config)
        app = application.configure()

        boot_manager = application.boot_manager
        hub = boot_manager._ensure_hub()
        hub.admin_site.finalize = AsyncMock()
        hub.admin_site.cards.start_publishers = AsyncMock()
        hub.admin_site.cards.shutdown_publishers = AsyncMock()
        boot_manager._config = SimpleNamespace(
            ensure_seed=AsyncMock(),
            reload=AsyncMock(),
        )

        await app.router.startup()
        try:
            recorded_config = init_arguments["config"]
            assert recorded_config["connections"][
                ExampleORMConfig.default_connection_name
            ] == custom_dsn
            apps = recorded_config["apps"]
            project_modules = set(apps["models"]["models"])
            assert set(MODELS_APP_MODULES).issubset(project_modules)
            system_modules = set(apps["system"]["models"])
            assert set(SYSTEM_APP_MODULES).issubset(system_modules)
            admin_modules = set(apps["admin"]["models"])
            assert set(ADMIN_APP_MODULES).issubset(admin_modules)
        finally:
            await app.router.shutdown()

        assert shutdown_calls == [True]


class TestExampleApplicationDiscovery:
    """Validate discovery of demo application resources."""

    @pytest.mark.asyncio
    async def test_demo_config_startup_invoked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure DemoConfig.startup executes when scanning nested packages."""

        application = ExampleApplication()
        application.register_packages(["example.apps"])
        app = application.configure()

        boot_manager = application.boot_manager
        hub = boot_manager._ensure_hub()
        hub.admin_site.finalize = AsyncMock()
        hub.admin_site.cards.start_publishers = AsyncMock()
        hub.admin_site.cards.shutdown_publishers = AsyncMock()
        boot_manager._config = SimpleNamespace(
            ensure_seed=AsyncMock(),
            reload=AsyncMock(),
        )

        from example.apps.demo import app as demo_app_module

        startup_mock = AsyncMock()
        monkeypatch.setattr(demo_app_module.default, "startup", startup_mock)
        previous_config = hub._app_configs.get("example.apps.demo")
        was_started = "example.apps.demo" in hub._started_configs
        hub._started_configs.discard("example.apps.demo")

        await app.router.startup()
        try:
            assert startup_mock.await_count == 1
        finally:
            await app.router.shutdown()
            if was_started:
                hub._started_configs.add("example.apps.demo")
            else:
                hub._started_configs.discard("example.apps.demo")
            if previous_config is None:
                hub._app_configs.pop("example.apps.demo", None)
            else:
                hub._app_configs["example.apps.demo"] = previous_config


# The End

