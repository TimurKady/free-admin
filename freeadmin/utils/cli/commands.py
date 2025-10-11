# -*- coding: utf-8 -*-
"""
commands

Click command factories for the freeadmin CLI.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Optional

import click

from .application_scaffolder import ApplicationScaffolder
from .create_superuser import SuperuserCreator
from .project_initializer import ProjectInitializer
from .reporting import CreationReport


class InitCommand:
    """Produce the `init` command for project scaffolding."""

    def __init__(self, initializer: ProjectInitializer, *, default_name: str = "myproject") -> None:
        """Store dependencies required to initialize new projects."""
        self._initializer = initializer
        self._default_name = default_name

    def execute(self, project_name: Optional[str]) -> None:
        """Handle the creation of a new project skeleton."""
        target_name = project_name or self._default_name
        report = self._initializer.create_project(target_name)
        self._echo_success(report, target_name)

    def to_click_command(self) -> click.Command:
        """Return a Click command configured for project initialization."""
        return click.Command(
            name="init",
            callback=self.execute,
            params=[click.Argument(["project_name"], required=False)],
            help="Initialize a new freeadmin project structure.",
        )

    def _echo_success(self, report: CreationReport, project_name: str) -> None:
        message = f"Project '{project_name}' scaffold ready at {report.root}"
        color = "green" if report.created_any() else "yellow"
        click.secho(message, fg=color)
        if report.skipped_any():
            click.secho("Existing items preserved:", fg="yellow")
            for path in report.skipped:
                click.secho(f"  - {path}", fg="yellow")


class AddCommand:
    """Produce the `add` command for application scaffolding."""

    def __init__(self, scaffolder: ApplicationScaffolder) -> None:
        """Store the scaffolder used to build application directories."""
        self._scaffolder = scaffolder

    def execute(self, app_name: str) -> None:
        """Handle the creation of a new application inside the project."""
        try:
            report = self._scaffolder.create_application(app_name)
        except RuntimeError as error:
            click.secho(str(error), fg="yellow")
            return
        self._echo_result(report, app_name)

    def to_click_command(self) -> click.Command:
        """Return a Click command configured for application creation."""
        return click.Command(
            name="add",
            callback=self.execute,
            params=[click.Argument(["app_name"], required=True)],
            help="Add a new application to the current freeadmin project.",
        )

    def _echo_result(self, report: CreationReport, app_name: str) -> None:
        message = f"Application '{app_name}' scaffold ready at {report.root}"
        color = "green" if report.created_any() else "yellow"
        click.secho(message, fg=color)
        if report.skipped_any():
            click.secho("Existing items preserved:", fg="yellow")
            for path in report.skipped:
                click.secho(f"  - {path}", fg="yellow")


class SuperuserCommand:
    """Produce the `create-superuser` command for administrative accounts."""

    def __init__(self, creator: SuperuserCreator) -> None:
        """Store the superuser creator for delegation."""
        self._creator = creator

    def execute(
        self,
        username: Optional[str],
        email: Optional[str],
        password: Optional[str],
        no_input: bool,
        update_if_exists: bool,
        reset_password_if_exists: bool,
    ) -> None:
        """Delegate to the creator and exit with the resulting status code."""
        exit_code = self._creator.create_superuser(
            username=username,
            email=email,
            password=password,
            no_input=no_input,
            update_if_exists=update_if_exists,
            reset_password_if_exists=reset_password_if_exists,
        )
        if exit_code == 0:
            click.secho("Superuser command completed successfully.", fg="green")
        else:
            raise click.exceptions.Exit(exit_code)

    def to_click_command(self) -> click.Command:
        """Return a Click command configured for superuser creation."""
        return click.Command(
            name="create-superuser",
            callback=self.execute,
            params=[
                click.Option(["--username"], help="Username for the superuser"),
                click.Option(["--email"], help="Email for the superuser"),
                click.Option(["--password"], help="Password for the superuser"),
                click.Option(["--no-input"], is_flag=True, help="Disable interactive prompts"),
                click.Option(["--update-if-exists"], is_flag=True, help="Update flags if the user exists"),
                click.Option(
                    ["--reset-password-if-exists"],
                    is_flag=True,
                    help="Reset password when updating an existing user",
                ),
            ],
            help="Create or update a freeadmin superuser.",
        )


# The End

