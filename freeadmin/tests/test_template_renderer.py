# -*- coding: utf-8 -*-
"""
tests.test_template_renderer

Unit tests for the shared template rendering service.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Mapping

from freeadmin.core.interface.templates import TemplateRenderer, TemplateService


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


# The End

