# -*- coding: utf-8 -*-
"""
templates.rendering

Helper utilities for rendering FreeAdmin templates outside the admin UI.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..conf import FreeAdminSettings, current_settings
from ..provider import TemplateProvider

ASSETS_DIR = Path(__file__).resolve().parent.parent / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class TemplateRenderer:
    """Provide cached access to FreeAdmin templates for public pages."""

    _templates: Jinja2Templates | None = None
    _provider: TemplateProvider | None = None

    @classmethod
    def get_provider(cls) -> TemplateProvider:
        """Return the shared template provider instance."""

        if cls._provider is None:
            settings: FreeAdminSettings | None = current_settings()
            cls._provider = TemplateProvider(
                templates_dir=str(TEMPLATES_DIR),
                static_dir=str(ASSETS_DIR),
                settings=settings,
            )
        return cls._provider

    @classmethod
    def get_templates(cls) -> Jinja2Templates:
        """Return a cached ``Jinja2Templates`` instance."""

        if cls._templates is None:
            cls._templates = cls.get_provider().get_templates()
        return cls._templates

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
        return cls.get_templates().TemplateResponse(template_name, final_context)


def render_template(
    template_name: str,
    context: Mapping[str, Any],
    *,
    request: Request | None = None,
) -> HTMLResponse:
    """Render ``template_name`` with ``context`` for use in FastAPI views."""

    return TemplateRenderer.render(template_name, context, request=request)


# The End


