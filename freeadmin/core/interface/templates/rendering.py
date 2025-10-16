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

from . import service as template_service_module
from .service import TemplateService
from ..settings import SettingsKey, system_config
from freeadmin.core.configuration.conf import current_settings


class TemplateRenderer:
    """Provide cached access to FreeAdmin templates for public pages."""

    _service: TemplateService | None = template_service_module.DEFAULT_TEMPLATE_SERVICE

    @classmethod
    def configure(cls, service: TemplateService) -> None:
        """Replace the template service used by the renderer."""

        cls._service = service

    @classmethod
    def get_service(cls) -> TemplateService:
        """Return the template service backing the renderer."""

        if cls._service is None:
            default_service = template_service_module.DEFAULT_TEMPLATE_SERVICE
            if default_service is not None:
                cls._service = default_service
            else:
                cls._service = TemplateService()
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
            payload.setdefault("page_title", title)

        defaults = cls._build_default_context(request)
        for key, value in defaults.items():
            payload.setdefault(key, value)

        return TemplateRenderer.render(template_name, payload, request=request)

    @classmethod
    def _build_default_context(cls, request: Request) -> dict[str, Any]:
        admin_site = getattr(getattr(request.app, "state", object()), "admin_site", None)
        settings_obj = getattr(admin_site, "_settings", None)
        if settings_obj is None:
            settings_obj = current_settings()

        admin_prefix = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX,
            getattr(settings_obj, "admin_path", "/admin"),
        ).rstrip("/")
        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")
        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        views_prefix = system_config.get_cached(SettingsKey.VIEWS_PREFIX, "/views")

        if admin_site is not None:
            site_title = admin_site.title
            brand_icon = admin_site.brand_icon
        else:
            site_title = system_config.get_cached(
                SettingsKey.DEFAULT_ADMIN_TITLE,
                getattr(settings_obj, "admin_site_title", "FreeAdmin"),
            )
            brand_icon = system_config.get_cached(
                SettingsKey.BRAND_ICON,
                getattr(settings_obj, "brand_icon", None),
            )

        return {
            "prefix": admin_prefix,
            "ORM_PREFIX": orm_prefix,
            "SETTINGS_PREFIX": settings_prefix,
            "VIEWS_PREFIX": views_prefix,
            "site_title": site_title,
            "brand_icon": brand_icon,
            "assets": {"css": [], "js": []},
            "system_config": system_config,
        }


def render_template(
    template_name: str,
    context: Mapping[str, Any],
    *,
    request: Request | None = None,
) -> HTMLResponse:
    """Render ``template_name`` with ``context`` for use in FastAPI views."""

    return TemplateRenderer.render(template_name, context, request=request)


# The End


