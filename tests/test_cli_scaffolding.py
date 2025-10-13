# -*- coding: utf-8 -*-
"""Tests ensuring CLI scaffolding creates package initializers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from freeadmin.utils.cli.application_scaffolder import ApplicationScaffolder
from freeadmin.utils.cli.project_initializer import ProjectInitializer


@dataclass
class ScaffoldingHelper:
    """Coordinate CLI scaffolding operations for assertions."""

    base_path: Path

    def create_project(self, project_name: str) -> Path:
        """Initialize a project and return the resulting root path."""

        initializer = ProjectInitializer(base_path=self.base_path)
        initializer.create_project(project_name)
        return self.base_path / project_name

    def add_application(self, project_root: Path, app_name: str) -> Path:
        """Create an application inside ``project_root`` and return its path."""

        scaffolder = ApplicationScaffolder(project_root=project_root)
        scaffolder.create_application(app_name)
        return project_root / "apps" / app_name


class TestCLIScaffolding:
    """Test suite covering the init and add CLI scaffolding behaviour."""

    def test_init_creates_package_initializers(self, tmp_path: Path) -> None:
        """Ensure the init command creates package markers for Python modules."""

        helper = ScaffoldingHelper(base_path=tmp_path)
        project_root = helper.create_project("demo_project")

        assert (project_root / "config" / "__init__.py").exists()
        assert (project_root / "apps" / "__init__.py").exists()

    def test_add_creates_application_package(self, tmp_path: Path) -> None:
        """Ensure the add command creates ``__init__.py`` in the new application."""

        helper = ScaffoldingHelper(base_path=tmp_path)
        project_root = helper.create_project("demo_project")
        app_root = helper.add_application(project_root, "blog")

        assert (app_root / "__init__.py").exists()


# The End

