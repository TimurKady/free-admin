# -*- coding: utf-8 -*-
"""
core.templates.rendering

Helper utilities for rendering FreeAdmin templates outside the admin UI.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Mapping

from fastapi import Request
from fastapi.responses import HTMLResponse

from .service import DEFAULT_TEMPLATE_SERVICE, TemplateService


class TemplateRenderer:
    """Provide cached access to FreeAdmin templates for public pages."""

    _service: TemplateService = DEFAULT_TEMPLATE_SERVICE

    @classmethod
    def configure(cls, service: TemplateService) -> None:
        """Replace the template service used by the renderer."""

        cls._service = service

    @classmethod
    def get_service(cls) -> TemplateService:
        """Return the template service backing the renderer."""

        return cls._service

    @classmethod
    def render(
        cls,
        template_name: str,
        context: Mapping[str, Any],
        *,
        request: Request | None = None,
    ) -> HTMLResponse:
        """Render ``template_name`` with ``context`` using FreeAdmin templates."""

        final_context = dict(context)
        if request is not None:
            final_context.setdefault("request", request)
        if "request" not in final_context:
            raise ValueError("Template context must include a 'request' key.")
        templates = cls.get_service().get_templates()
        return templates.TemplateResponse(template_name, final_context)


class PageTemplateResponder:
    """Render FreeAdmin page templates with standardised context defaults."""

    @classmethod
    def render(
        cls,
        template_name: str,
        *,
        request: Request,
        context: Mapping[str, Any] | None = None,
        title: str | None = None,
    ) -> HTMLResponse:
        """Render ``template_name`` using ``context`` and injected defaults."""

        payload = dict(context or {})
        payload.setdefault("request", request)
        payload.setdefault("user", getattr(request.state, "user", None))
        if title is not None:
            payload.setdefault("title", title)
        return TemplateRenderer.render(template_name, payload, request=request)


def render_template(
    template_name: str,
    context: Mapping[str, Any],
    *,
    request: Request | None = None,
) -> HTMLResponse:
    """Render ``template_name`` with ``context`` for use in FastAPI views."""

    return TemplateRenderer.render(template_name, context, request=request)


# The End


