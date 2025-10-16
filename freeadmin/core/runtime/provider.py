# -*- coding: utf-8 -*-
"""
provider

Utility class for providing templates and static files for the admin.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

from ..configuration.conf import FreeAdminSettings, current_settings
from ..interface.settings import SettingsKey, system_config

class TemplateProvider:
    """Encapsulates template and static file handling."""

    def __init__(
        self,
        *,
        templates_dir: str | Path | Iterable[str | Path],
        static_dir: str | Path,
        settings: FreeAdminSettings | None = None,
    ) -> None:
        """Store template and static paths together with active settings."""

        self._template_dirs = self._coerce_template_dirs(templates_dir)
        self.static_dir = str(static_dir)
        self._settings = settings or current_settings()

    def get_templates(self) -> Jinja2Templates:
        """Return a configured ``Jinja2Templates`` instance."""
        templates = Jinja2Templates(directory=list(self._template_dirs))
        templates.env.globals["settings"] = self._settings
        return templates

    @property
    def template_directories(self) -> tuple[str, ...]:
        """Return template directories available to the provider."""

        return tuple(self._template_dirs)

    def add_template_directory(self, directory: str | Path) -> None:
        """Include ``directory`` in the template search path if missing."""

        normalized = str(directory)
        if normalized not in self._template_dirs:
            self._template_dirs.append(normalized)

    @staticmethod
    def _coerce_template_dirs(
        templates_dir: str | Path | Iterable[str | Path]
    ) -> list[str]:
        """Normalise ``templates_dir`` into a mutable list of strings."""

        if isinstance(templates_dir, (str, Path)):
            return [str(templates_dir)]
        return [str(path) for path in templates_dir]

    def mount_static(self, app: FastAPI, prefix: str) -> None:
        """Mount static files onto the provided application."""
        static_segment = system_config.get_cached(
            SettingsKey.STATIC_URL_SEGMENT, self._settings.static_url_segment
        )
        route_name = system_config.get_cached(
            SettingsKey.STATIC_ROUTE_NAME, self._settings.static_route_name
        )
        app.mount(
            f"{prefix}{static_segment}",
            StaticFiles(
                directory=self.static_dir,
                packages=[("freeadmin", "static")],
            ),
            name=route_name,
        )

    def mount_favicon(self, app: FastAPI) -> None:
        """Expose the favicon for the admin interface."""
        favicon = Path(self.static_dir) / "favicon.ico"

        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon_route() -> FileResponse:  # pragma: no cover - simple file response
            return FileResponse(favicon)

    def mount_media(self, app: FastAPI) -> None:
        """Mount uploaded media files onto the application."""
        media_root = Path(
            system_config.get_cached(
                SettingsKey.MEDIA_ROOT, str(self._settings.media_root)
            )
        ).resolve()
        media_root.mkdir(parents=True, exist_ok=True)

        media_url = system_config.get_cached(
            SettingsKey.MEDIA_URL, self._settings.media_url
        )
        media_prefix = "/" + str(media_url).strip("/")

        app.mount(
            media_prefix,
            StaticFiles(directory=str(media_root)),
            name="admin-media",
        )

# The End

