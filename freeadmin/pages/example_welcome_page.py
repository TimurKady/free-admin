# -*- coding: utf-8 -*-
"""
pages.example_welcome_page

Example public page demonstrating FreeAdmin's extended router aggregator.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from freeadmin.templates import render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the welcome page example for anonymous visitors."""

    context = {"request": request, "title": "Welcome", "user": None}
    return render_template("welcome.html", context)


# The End


