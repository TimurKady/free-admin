# -*- coding: utf-8 -*-
"""
project_initializer

Project scaffolding helpers for the init CLI command.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

from .reporting import CreationReport


ROUTER_TEMPLATE_CLASS_NAME = "ProjectRouterAggregator"


class PackageInitializer:
    """Create ``__init__`` markers for project package directories."""

    def __init__(self, package_directories: Iterable[str]) -> None:
        """Remember target directories requiring package initialization."""

        self._package_directories = tuple(package_directories)

    def ensure_packages(self, project_root: Path, report: CreationReport) -> None:
        """Create empty ``__init__.py`` files for configured directories."""

        for directory in self._package_directories:
            package_path = project_root / directory / "__init__.py"
            if package_path.exists():
                report.add_skipped(package_path)
                continue
            package_path.write_text("", encoding="utf-8")
            report.add_created(package_path)


class ConfigTemplateProvider:
    """Generate configuration file templates for project scaffolding."""

    def __init__(self, project_name: str) -> None:
        """Remember the target project name for template rendering."""
        self._project_name = project_name

    def templates(self) -> Dict[str, str]:
        """Return all available configuration templates keyed by filename."""
        return {
            "main.py": self._main_template().format(project_name=self._project_name),
            "orm.py": self._orm_template().format(project_name=self._project_name),
            "settings.py": self._settings_template().format(project_name=self._project_name),
            "routers.py": self._routers_template().format(
                project_name=self._project_name,
                router_class=ROUTER_TEMPLATE_CLASS_NAME,
            ),
        }

    def _main_template(self) -> str:
        return '''# -*- coding: utf-8 -*-
"""
Application bootstrap for {project_name}.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import List

from fastapi import FastAPI

from freeadmin.boot import BootManager

from .orm import ORMLifecycle, ORMSettings
from .settings import ProjectSettings


class ApplicationFactory:
    """Create FastAPI applications for the project."""

    def __init__(
        self,
        *,
        settings: ProjectSettings | None = None,
        orm_settings: ORMSettings | None = None,
        packages: Iterable[str] | None = None,
    ) -> None:
        """Configure dependencies required to build the application."""

        self._settings = settings or ProjectSettings()
        self._orm_settings = orm_settings or ORMSettings()
        self._orm_lifecycle: ORMLifecycle = self._orm_settings.create_lifecycle()
        self._boot = BootManager(adapter_name=self._orm_lifecycle.adapter_name)
        self._app = FastAPI(title=self._settings.project_title)
        self._packages: List[str] = list(packages or ["apps", "pages"])
        self._orm_events_bound = False

    def build(self) -> FastAPI:
        """Return a FastAPI instance wired with FreeAdmin integration."""

        self._bind_orm_events()
        self._boot.init(
            self._app,
            adapter=self._orm_lifecycle.adapter_name,
            packages=self._packages,
        )
        return self._app

    def _bind_orm_events(self) -> None:
        """Attach ORM lifecycle hooks to the FastAPI application."""

        if self._orm_events_bound:
            return
        self._orm_lifecycle.bind(self._app)
        self._orm_events_bound = True


app = ApplicationFactory().build()


# The End

'''

    def _orm_template(self) -> str:
        return '''# -*- coding: utf-8 -*-
"""
Database configuration entry point for {project_name}.
"""

from __future__ import annotations

from typing import Dict

from fastapi import FastAPI


class ORMSettings:
    """Provide placeholder ORM configuration values."""

    def __init__(self, *, adapter_name: str = "tortoise") -> None:
        """Store the adapter identifier used by the ORM lifecycle."""

        self._adapter_name = adapter_name

    @property
    def adapter_name(self) -> str:
        """Return the adapter identifier configured for the project."""

        return self._adapter_name

    def template(self) -> Dict[str, str]:
        """Return a dictionary with example ORM configuration."""

        return {{"default": "sqlite:///db.sqlite3"}}

    def create_lifecycle(self) -> ORMLifecycle:
        """Return an ORM lifecycle configured with these settings."""

        return ORMLifecycle(settings=self)


class ORMLifecycle:
    """Manage ORM startup and shutdown hooks for FastAPI."""

    def __init__(self, *, settings: ORMSettings) -> None:
        """Persist settings required to bind lifecycle handlers."""

        self._settings = settings

    @property
    def adapter_name(self) -> str:
        """Expose the adapter identifier for BootManager wiring."""

        return self._settings.adapter_name

    async def startup(self) -> None:
        """Placeholder coroutine executed on FastAPI startup."""

        return None

    async def shutdown(self) -> None:
        """Placeholder coroutine executed on FastAPI shutdown."""

        return None

    def bind(self, app: FastAPI) -> None:
        """Register lifecycle handlers on a FastAPI application."""

        app.add_event_handler("startup", self.startup)
        app.add_event_handler("shutdown", self.shutdown)


__all__ = ["ORMSettings", "ORMLifecycle"]


# The End

'''

    def _settings_template(self) -> str:
        return '''# -*- coding: utf-8 -*-
"""
Primary configuration object for {project_name}.
"""

from __future__ import annotations

from pydantic import BaseSettings


class ProjectSettings(BaseSettings):
    """Basic settings model for the generated project."""

    debug: bool = True
    database_url: str = "sqlite:///db.sqlite3"
    project_title: str = "{project_name} administration"


settings = ProjectSettings()


# The End

'''

    def _routers_template(self) -> str:
        return '''# -*- coding: utf-8 -*-
"""
routers

Routing helpers for {project_name}.
"""

from __future__ import annotations

from typing import Optional, Type

from fastapi import APIRouter, FastAPI

from freeadmin.core.site import AdminSite
from freeadmin.router import AdminRouter


class {router_class}:
    """Manage mounting the FreeAdmin router for {project_name}."""

    def __init__(
        self,
        *,
        admin_router_cls: Type[AdminRouter] = AdminRouter,
    ) -> None:
        """Store the admin router class used for mounting."""

        self._admin_router_cls = admin_router_cls
        self._admin_router: Optional[AdminRouter] = None
        self._router: Optional[APIRouter] = None
        self._site: Optional[AdminSite] = None

    def mount(self, app: FastAPI, site: AdminSite) -> APIRouter:
        """Attach the admin router for ``site`` onto ``app`` once."""

        router = self.get_admin_router(site)
        if getattr(app.state, "admin_site", None) is site:
            return router

        admin_router = self._ensure_admin_router(site)
        app.state.admin_site = site
        app.include_router(router, prefix=admin_router.prefix)
        provider = admin_router._provider
        provider.mount_static(app, admin_router.prefix)
        provider.mount_favicon(app)
        provider.mount_media(app)
        return router

    def get_admin_router(self, site: AdminSite) -> APIRouter:
        """Return a cached admin router for the given ``site``."""

        admin_router = self._ensure_admin_router(site)
        if self._router is not None:
            return self._router

        if site.templates is None:
            site.templates = admin_router._provider.get_templates()
        self._router = site.build_router(admin_router._provider)
        return self._router

    def _ensure_admin_router(self, site: AdminSite) -> AdminRouter:
        """Instantiate or reuse the admin router for ``site``."""

        if self._admin_router is None or self._site is not site:
            self._site = site
            self._router = None
            self._admin_router = self._admin_router_cls(site)
        return self._admin_router


_ROUTER_AGGREGATOR = {router_class}()


def get_admin_router(site: AdminSite) -> APIRouter:
    """Return the admin router for ``site`` using the shared aggregator."""

    return _ROUTER_AGGREGATOR.get_admin_router(site)


__all__ = ["{router_class}", "get_admin_router"]


# The End

'''


class ProjectInitializer:
    """Build the base filesystem layout for a Freeadmin project."""

    _DIRECTORIES = (
        "config",
        "apps",
        "pages",
        "static",
        "templates",
    )

    _PACKAGE_DIRECTORIES = (
        "config",
        "apps",
    )

    _README_TEMPLATE = """# {project_name}\n\nThis project was generated by the freeadmin CLI utility. Customize the configuration in the `config/` directory.\n"""

    def __init__(self, base_path: Path | None = None) -> None:
        """Prepare the initializer with the filesystem base path."""
        self._base_path = base_path or Path.cwd()
        self._package_initializer = PackageInitializer(self._PACKAGE_DIRECTORIES)

    def create_project(self, project_name: str) -> CreationReport:
        """Create or update the project skeleton under the base path."""
        project_root = self._base_path / project_name
        report = CreationReport(project_root)

        if project_root.exists():
            report.add_skipped(project_root)
        else:
            project_root.mkdir(parents=True, exist_ok=True)
            report.add_created(project_root)

        for directory in self._DIRECTORIES:
            directory_path = project_root / directory
            if directory_path.exists():
                report.add_skipped(directory_path)
                continue
            directory_path.mkdir(parents=True, exist_ok=True)
            report.add_created(directory_path)

        self._package_initializer.ensure_packages(project_root, report)
        self._create_config_files(project_root, report, project_name)
        self._create_readme(project_root, report, project_name)
        return report

    def _create_config_files(
        self,
        project_root: Path,
        report: CreationReport,
        project_name: str,
    ) -> None:
        config_dir = project_root / "config"
        templates = ConfigTemplateProvider(project_name).templates()
        for file_name, template in templates.items():
            file_path = config_dir / file_name
            if file_path.exists():
                report.add_skipped(file_path)
                continue
            file_path.write_text(
                template,
                encoding="utf-8",
            )
            report.add_created(file_path)

    def _create_readme(
        self,
        project_root: Path,
        report: CreationReport,
        project_name: str,
    ) -> None:
        readme_path = project_root / "README.md"
        if readme_path.exists():
            report.add_skipped(readme_path)
            return
        readme_path.write_text(
            self._README_TEMPLATE.format(project_name=project_name),
            encoding="utf-8",
        )
        report.add_created(readme_path)


# The End

