# -*- coding: utf-8 -*-
"""
cli

CLI utilities for the freeadmin toolkit.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from .application_scaffolder import ApplicationScaffolder
from .commands import AddCommand, InitCommand, SuperuserCommand
from .create_superuser import SuperuserCreator
from .entry import FreeAdminCLI, cli
from .project_initializer import ProjectInitializer
from .reporting import CreationReport

__all__ = [
    "ApplicationScaffolder",
    "AddCommand",
    "InitCommand",
    "SuperuserCommand",
    "SuperuserCreator",
    "FreeAdminCLI",
    "cli",
    "ProjectInitializer",
    "CreationReport",
]


# The End

