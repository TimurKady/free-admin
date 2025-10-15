# -*- coding: utf-8 -*-
"""Tests ensuring AdminSite.finalize tolerates missing migrations."""

from __future__ import annotations

import logging

import pytest
from tortoise import Tortoise

from freeadmin.core.boot import admin as boot_admin
from freeadmin.core import site as site_module
from freeadmin.core.site import AdminSite
from tests.system_models import system_models


@pytest.mark.asyncio
async def test_finalize_logs_hint_when_admin_tables_missing(caplog) -> None:
    """AdminSite.finalize should log a migration hint when tables are absent."""

    await Tortoise._reset_apps()
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={
            "models": [],
            "admin": list(system_models.module_names()),
        },
    )

    site = AdminSite(boot_admin.adapter, title="Test")

    caplog.set_level(logging.ERROR, logger=site_module.logger.name)

    try:
        await site.finalize()
    finally:
        await Tortoise.close_connections()
        await Tortoise._reset_apps()

    assert "Skipping admin content type synchronisation" in caplog.text
    assert "Run your migrations before starting FreeAdmin." in caplog.text


# The End
