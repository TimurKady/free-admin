# -*- coding: utf-8 -*-
"""admin guard middleware fallbacks

Validate AdminGuardMiddleware resilience when system configuration cache is empty."""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest
from starlette.requests import Request
from starlette.responses import Response

from freeadmin.core.boot import admin as boot_admin
from freeadmin.core.runtime.middleware import AdminGuardMiddleware
from freeadmin.core.interface.settings import system_config
from tests.conftest import admin_state


class AdapterStub:
    """Minimal adapter stub satisfying middleware dependencies."""

    def __init__(self) -> None:
        """Prepare stubbed user model references."""

        self.user_model = type("UserModel", (), {})

    def filter(self, model: Any, **kwargs: Any) -> tuple[str, Any, dict[str, Any]]:
        """Return a simple representation of a filtered query."""

        return ("query", model, kwargs)

    async def exists(self, query: tuple[str, Any, dict[str, Any]]) -> bool:
        """Report that no matching records exist in the datastore."""

        return False

    async def get_or_none(self, model: Any, **kwargs: Any) -> Any | None:
        """Always return ``None`` to mimic an anonymous session user."""

        return None


class TestAdminGuardMiddlewareFallback:
    """Ensure admin guard behavior degrades gracefully without cached settings."""

    adapter: AdapterStub

    @classmethod
    def setup_class(cls) -> None:
        """Install adapter stub and reset shared state before tests."""

        admin_state.reset()
        cls.adapter = AdapterStub()
        boot_admin._adapter = cls.adapter

    @classmethod
    def teardown_class(cls) -> None:
        """Restore the global admin state after the test suite completes."""

        admin_state.reset()

    @pytest.mark.asyncio
    async def test_redirect_when_reload_fails(self, monkeypatch) -> None:
        """Redirect to setup using default paths after a reload failure."""

        async def _failing_reload() -> None:
            """Simulate a database error during system configuration reload."""

            raise sqlite3.OperationalError("system_setting table missing")

        monkeypatch.setattr(system_config, "reload", _failing_reload)
        system_config._cache.clear()  # type: ignore[attr-defined]

        with pytest.raises(sqlite3.OperationalError):
            await system_config.reload()

        async def _app(scope, receive, send) -> None:  # pragma: no cover - stub
            """Provide a placeholder ASGI application for the middleware stack."""

            return None

        middleware = AdminGuardMiddleware(_app)

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/admin/",
            "root_path": "",
            "scheme": "http",
            "server": ("testserver", 80),
            "headers": [],
            "query_string": b"",
        }
        scope["session"] = {}

        async def _receive() -> dict[str, Any]:
            """Provide an empty HTTP request body for the ASGI scope."""

            return {"type": "http.request", "body": b"", "more_body": False}

        request = Request(scope, receive=_receive)

        async def _call_next(_: Request) -> Response:
            """Return a no-op response when middleware allows continuation."""

            return Response("ok")

        response = await middleware.dispatch(request, _call_next)
        assert response.status_code == 307
        assert response.headers.get("location") == "/admin/setup"


# The End

