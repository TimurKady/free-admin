# -*- coding: utf-8 -*-
"""
tests.test_template_renderer

Unit tests for the shared template rendering service.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI
from fastapi.testclient import TestClient

from freeadmin.core.boot import admin as boot_admin
from freeadmin.core.interface.site import AdminSite
from freeadmin.core.interface.templates import TemplateRenderer, TemplateService
from freeadmin.core.interface.templates import service as template_service_module
from freeadmin.core.network.router.aggregator import RouterAggregator
from tests.conftest import admin_state


class DummyTemplates:
    """Collect template rendering calls for assertions."""

    def __init__(self) -> None:
        """Initialise the call history container."""

        self.calls: list[tuple[str, Mapping[str, Any]]] = []

    def TemplateResponse(self, template_name: str, context: Mapping[str, Any]) -> dict[str, Any]:
        """Record the call and echo a serialisable response."""

        self.calls.append((template_name, context))
        return {"template": template_name, "context": context}


class TrackingProvider:
    """Minimal provider used to validate service caching."""

    def __init__(
        self,
        *,
        templates_dir: Any,
        static_dir: str,
        settings: Any,
    ) -> None:
        """Create the provider with inert template and static references."""

        del templates_dir, static_dir, settings
        self.templates = DummyTemplates()
        self.get_templates_calls = 0

    def get_templates(self) -> DummyTemplates:
        """Return the dummy templates while tracking call frequency."""

        self.get_templates_calls += 1
        return self.templates

    def mount_static(self, *_: Any, **__: Any) -> None:
        """Stub implementation to satisfy the provider interface."""

    def mount_favicon(self, *_: Any, **__: Any) -> None:
        """Stub implementation to satisfy the provider interface."""

    def mount_media(self, *_: Any, **__: Any) -> None:
        """Stub implementation to satisfy the provider interface."""


def test_template_renderer_uses_shared_service_cache() -> None:
    """Template renderer should reuse the cached templates instance."""

    service = TemplateService(provider_cls=TrackingProvider)
    original_service = TemplateRenderer.get_service()
    TemplateRenderer.configure(service)

    try:
        first = TemplateRenderer.render(
            "welcome.html",
            {"request": object(), "message": "hello"},
        )
        second = TemplateRenderer.render(
            "welcome.html",
            {"request": object(), "message": "again"},
        )

        provider = service.get_provider()
        assert provider.get_templates_calls == 1
        assert provider.templates.calls[0][1]["message"] == "hello"
        assert provider.templates.calls[1][1]["message"] == "again"
        assert first["context"]["message"] == "hello"
        assert second["context"]["message"] == "again"
    finally:
        TemplateRenderer.configure(original_service)


class TestRouterAggregatorTemplateIntegration:
    """Validate TemplateRenderer configuration within router aggregators."""

    def test_public_page_uses_aggregator_service(self, tmp_path: Path) -> None:
        """Ensure public page rendering relies on the aggregator's template service."""

        original_renderer_service = getattr(TemplateRenderer, "_service", None)
        original_default_service = template_service_module.DEFAULT_TEMPLATE_SERVICE
        admin_state.reset()

        templates_root = tmp_path / "custom_templates"
        pages_dir = templates_root / "pages"
        pages_dir.mkdir(parents=True)
        unique_phrase = "aggregator template wiring is active"
        (pages_dir / "greeting.html").write_text(
            f"<html><body>{{{{ title }}}} :: {unique_phrase}</body></html>",
            encoding="utf-8",
        )

        custom_service = TemplateService(templates_dir=templates_root)
        site = AdminSite(boot_admin.adapter, title="Renderer Integration")

        @site.register_public_view(
            path="/greeting",
            name="Greeting",
            template="pages/greeting.html",
        )
        def greeting_page(*_: object, **__: object) -> Mapping[str, Any]:
            """Provide context for the greeting public page."""

            return {}

        try:
            aggregator = RouterAggregator(site=site, template_service=custom_service)
            assert TemplateRenderer.get_service() is custom_service

            app = FastAPI()
            aggregator.mount(app)

            with TestClient(app) as client:
                response = client.get("/greeting")

            assert response.status_code == 200
            assert unique_phrase in response.text
        finally:
            admin_state.reset()
            TemplateRenderer._service = original_renderer_service
            template_service_module.DEFAULT_TEMPLATE_SERVICE = original_default_service


# The End

