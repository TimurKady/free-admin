# -*- coding: utf-8 -*-
"""
cli

Click entry point for the freeadmin toolkit.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import click

from .utils.cli import (
    AddCommand,
    ApplicationScaffolder,
    InitCommand,
    ProjectInitializer,
    SuperuserCommand,
    SuperuserCreator,
)


class FreeAdminCLI:
    """Aggregate all CLI commands exposed by the package."""

    def __init__(self) -> None:
        """Create command instances required to build the CLI group."""
        initializer = ProjectInitializer()
        scaffolder = ApplicationScaffolder()
        creator = SuperuserCreator()
        self._init_command = InitCommand(initializer)
        self._add_command = AddCommand(scaffolder)
        self._superuser_command = SuperuserCommand(creator)

    def create_cli(self) -> click.Group:
        """Build the Click group with all registered commands."""
        group = click.Group(
            name="freeadmin",
            help="Command line tools for managing freeadmin projects.",
        )
        group.add_command(self._init_command.to_click_command())
        group.add_command(self._add_command.to_click_command())
        group.add_command(self._superuser_command.to_click_command())
        return group


cli = FreeAdminCLI().create_cli()


# The End

