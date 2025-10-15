# -*- coding: utf-8 -*-
"""conftest

Shared testing utilities for FreeAdmin test-suite fixtures.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

import pytest

from freeadmin.core.boot import admin as boot_admin
from freeadmin.core.settings import system_config


class AdminState:
    """Manage global admin boot configuration during tests."""

    def __init__(self) -> None:
        """Capture references to mutable singletons used by the admin."""

        self._boot = boot_admin
        self._system_config = system_config

    def reset(self) -> None:
        """Restore boot manager and system configuration cache to defaults."""

        self._boot.reset()
        self._system_config._cache.clear()  # type: ignore[attr-defined]


class AsyncioTestPlugin:
    """Minimal asyncio runner enabling ``async def`` tests without extras."""

    def __init__(self) -> None:
        """Configure the event-loop factory used for async test execution."""

        self._loop_factory = asyncio.new_event_loop

    def pytest_pyfunc_call(self, pyfuncitem: pytest.Function) -> bool | None:
        """Execute coroutine test functions inside a dedicated event loop."""

        if not inspect.iscoroutinefunction(pyfuncitem.obj):
            return None
        signature = inspect.signature(pyfuncitem.obj)
        kwargs = {
            name: pyfuncitem.funcargs[name]
            for name in signature.parameters
            if name in pyfuncitem.funcargs
        }
        loop = self._loop_factory()
        try:
            loop.run_until_complete(pyfuncitem.obj(**kwargs))
            pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
            if pending:
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
        return True


class PytestPluginRegistrar:
    """Register custom pytest plugins following project conventions."""

    def __init__(self) -> None:
        """Instantiate and expose plugin objects for registration."""

        self.asyncio_plugin = AsyncioTestPlugin()

    def configure(self, config: pytest.Config) -> None:
        """Register required plugins with the pytest plugin manager."""

        config.addinivalue_line(
            "markers", "asyncio: execute test using the built-in asyncio loop"
        )
        config.pluginmanager.register(self.asyncio_plugin, "freeadmin-asyncio-plugin")


admin_state = AdminState()
_plugin_registrar = PytestPluginRegistrar()


def pytest_configure(config: pytest.Config) -> None:
    """Integrate custom plugins with pytest's plugin manager."""

    _plugin_registrar.configure(config)


__all__ = ["admin_state"]


# The End
