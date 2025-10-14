# -*- coding: utf-8 -*-
"""
tests.test_router_aggregator

Unit tests for the router aggregator utility.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from freeadmin.router import RouterAggregator


def _build_site(router: APIRouter) -> MagicMock:
    site = MagicMock()
    site.templates = None
    site.build_router.return_value = router
    return site


def test_mount_is_idempotent() -> None:
    """Calling ``mount`` repeatedly must not duplicate admin resources."""

    app = FastAPI()
    admin_router = APIRouter()

    @admin_router.get("/dashboard")
    def dashboard() -> dict[str, str]:
        return {"status": "ok"}

    site = _build_site(admin_router)
    aggregator = RouterAggregator(site=site, prefix="/admin")
    aggregator._provider.mount_static = MagicMock()  # type: ignore[attr-defined]
    aggregator._provider.mount_favicon = MagicMock()  # type: ignore[attr-defined]
    aggregator._provider.mount_media = MagicMock()  # type: ignore[attr-defined]

    aggregator.mount(app)
    initial_route_count = len(app.router.routes)
    aggregator.mount(app)
    subsequent_route_count = len(app.router.routes)

    assert site.build_router.call_count == 1
    assert aggregator.get_admin_router() is admin_router
    assert initial_route_count == subsequent_route_count
    aggregator._provider.mount_static.assert_called_once_with(app, "/admin")  # type: ignore[attr-defined]
    aggregator._provider.mount_favicon.assert_called_once_with(app)  # type: ignore[attr-defined]
    aggregator._provider.mount_media.assert_called_once_with(app)  # type: ignore[attr-defined]
    assert app.state.admin_site is site


def test_subclass_can_register_extra_routers() -> None:
    """Subclasses should be able to expose bespoke routers."""

    app = FastAPI()
    admin_router = APIRouter()

    @admin_router.get("/home")
    def home() -> dict[str, str]:
        return {"status": "home"}

    extra_router = APIRouter()

    @extra_router.get("/extras/ping")
    def ping() -> dict[str, str]:
        return {"pong": "ok"}

    site = _build_site(admin_router)

    class CustomRouterAggregator(RouterAggregator):
        """Router aggregator providing an extra router."""

        def __init__(self, *, site: MagicMock) -> None:
            """Attach the admin site and register the extra router."""

            super().__init__(site=site, prefix="/admin")
            self.add_additional_router(extra_router, "")

    aggregator = CustomRouterAggregator(site=site)
    aggregator._provider.mount_static = MagicMock()  # type: ignore[attr-defined]
    aggregator._provider.mount_favicon = MagicMock()  # type: ignore[attr-defined]
    aggregator._provider.mount_media = MagicMock()  # type: ignore[attr-defined]
    aggregator.mount(app)

    client = TestClient(app)
    response = client.get("/extras/ping")
    assert response.status_code == 200
    assert response.json() == {"pong": "ok"}

    aggregator.mount(app)
    assert site.build_router.call_count == 1


def test_constructor_additional_router_registration() -> None:
    """Routers passed into the constructor should be mounted."""

    app = FastAPI()
    admin_router = APIRouter()

    @admin_router.get("/root")
    def root() -> dict[str, str]:
        return {"root": "ok"}

    reports_router = APIRouter()

    @reports_router.get("/reports")
    def reports() -> dict[str, str]:
        return {"reports": "ok"}

    site = _build_site(admin_router)
    aggregator = RouterAggregator(
        site=site,
        prefix="/admin",
        additional_routers=((reports_router, "/extras"),),
    )
    aggregator._provider.mount_static = MagicMock()  # type: ignore[attr-defined]
    aggregator._provider.mount_favicon = MagicMock()  # type: ignore[attr-defined]
    aggregator._provider.mount_media = MagicMock()  # type: ignore[attr-defined]
    aggregator.mount(app)

    client = TestClient(app)
    response = client.get("/extras/reports")
    assert response.status_code == 200
    assert response.json() == {"reports": "ok"}



# The End

