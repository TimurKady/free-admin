# -*- coding: utf-8 -*-
"""
test_cli_init

Tests for the project initialization CLI scaffolding.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path

from freeadmin.utils.cli.project_initializer import (
    ProjectInitializer,
    ROUTER_TEMPLATE_CLASS_NAME,
)


class TestProjectInitializerConfigTemplates:
    """Verify that configuration templates are rendered when scaffolding."""

    def test_config_templates_have_minimal_content(self, tmp_path: Path) -> None:
        """Ensure `init` scaffolding populates config files with starter code."""
        initializer = ProjectInitializer(base_path=tmp_path)
        initializer.create_project("demo")
        config_dir = tmp_path / "demo" / "config"

        main_content = (config_dir / "main.py").read_text(encoding="utf-8")
        orm_content = (config_dir / "orm.py").read_text(encoding="utf-8")
        routers_path = config_dir / "routers.py"
        assert routers_path.exists()
        routers_content = routers_path.read_text(encoding="utf-8")
        settings_content = (config_dir / "settings.py").read_text(encoding="utf-8")

        assert "BootManager" in main_content
        assert "self._boot.init" in main_content
        assert '"apps", "pages"' in main_content
        assert "self._orm_lifecycle.bind" in main_content
        assert "from .orm import ORM" in main_content
        assert "ORM_CONFIG" in orm_content
        assert "ORM: ORMConfig = ORMConfig.build" in orm_content
        assert ROUTER_TEMPLATE_CLASS_NAME in routers_content
        assert "RouterAggregator" in routers_content
        assert "super().mount" in routers_content
        assert "self.add_additional_router(reports_router, \"/reports\")" in routers_content
        assert "ProjectSettings" in settings_content
        assert "project_title" in settings_content


# The End

