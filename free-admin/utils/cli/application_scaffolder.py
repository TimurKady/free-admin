# -*- coding: utf-8 -*-
"""
application_scaffolder

Application scaffolding helpers for the add CLI command.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .reporting import CreationReport


class ApplicationScaffolder:
    """Create application skeletons inside an existing project."""

    _FILE_TEMPLATES: Dict[str, str] = {
        "__init__.py": "",
        "app.py": "# entry point for {app_name}\n",
        "models.py": "# models for {app_name}\n",
        "admin.py": "# admin definitions for {app_name}\n",
        "views.py": "# views for {app_name}\n",
        "cards.py": "# cards for {app_name}\n",
    }

    def __init__(self, project_root: Path | None = None) -> None:
        """Prepare scaffolder with an optional project root."""
        self._project_root = project_root or Path.cwd()

    def create_application(self, app_name: str) -> CreationReport:
        """Create the application structure under the project's apps directory."""
        apps_directory = self._project_root / "apps"
        if not apps_directory.exists():
            raise RuntimeError(
                "The current directory does not contain an 'apps' folder; run the command from the project root."
            )

        app_root = apps_directory / app_name
        report = CreationReport(app_root)

        if app_root.exists():
            report.add_skipped(app_root)
        else:
            app_root.mkdir(parents=True, exist_ok=True)
            report.add_created(app_root)

        for file_name, template in self._FILE_TEMPLATES.items():
            file_path = app_root / file_name
            if file_path.exists():
                report.add_skipped(file_path)
                continue
            file_path.write_text(
                template.format(app_name=app_name),
                encoding="utf-8",
            )
            report.add_created(file_path)

        return report


# The End

