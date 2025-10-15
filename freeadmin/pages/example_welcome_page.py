# -*- coding: utf-8 -*-
"""
pages.example_welcome_page

Example public page demonstrating FreeAdmin's extended router aggregator.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from fastapi import Request

from freeadmin.hub import admin_site


@admin_site.register_public_view(
    path="/",
    name="Welcome",
    template="welcome.html",
)
async def index(request: Request, user: object | None = None) -> dict[str, object]:
    """Return template context for the welcome example page."""

    return {"request": request, "user": user}


# The End


