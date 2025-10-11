# -*- coding: utf-8 -*-
"""
test_normalize_payload

Ensure BaseModelAdmin.normalize_payload flattens and coerces values.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

import pytest
from tortoise import Tortoise

from apps.characters.models import Character
from apps.characters.admin import CharacterAdmin
from freeadmin.boot import admin as boot_admin


class TestNormalizePayload:
    """Verify recursive flattening and type coercion."""

    @pytest.mark.asyncio
    async def test_normalize_payload(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={
                "models": ["apps.characters.models.characters"],
                "admin": ["freeadmin.adapters.tortoise.users"],
            },
        )
        await Tortoise.generate_schemas()

        admin = CharacterAdmin(Character, boot_admin)
        payload = {
            "mbti_sn": "0.8",
            "group_main": {
                "name": "Rick",
                "group_misc": {"mbti_ie": "0.7"},
                "is_enabled": "0",
            },
        }
        normalized = admin.normalize_payload(payload)

        assert normalized["name"] == "Rick"
        assert normalized["mbti_ie"] == pytest.approx(0.7)
        assert normalized["is_enabled"] is False
        assert normalized["mbti_sn"] == pytest.approx(0.8)

        await Tortoise.close_connections()


# The End
