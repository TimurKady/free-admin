# -*- coding: utf-8 -*-
"""
pages

Example view registrations for the FreeAdmin demo project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from .home import ExampleWelcomePage, example_welcome_page
from .public_welcome import (
    ExamplePublicWelcomeContext,
    example_public_welcome_context,
)
from .welcome_page import (
    ExamplePublicWelcomePage,
    example_public_welcome_page,
    public_welcome_router,
)

__all__ = [
    "ExampleWelcomePage",
    "example_welcome_page",
    "ExamplePublicWelcomeContext",
    "example_public_welcome_context",
    "ExamplePublicWelcomePage",
    "example_public_welcome_page",
    "public_welcome_router",
]

# The End

