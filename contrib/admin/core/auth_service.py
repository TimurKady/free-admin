# -*- coding: utf-8 -*-
"""
auth_service

Service utilities for admin authentication.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any

from ..adapters import BaseAdapter
from ..utils.passwords import password_hasher


class AuthService:
    """Authentication service using a provided adapter."""

    def __init__(self, adapter: BaseAdapter) -> None:
        self.adapter = adapter
        self.user_model = adapter.user_model

    async def authenticate_user(self, username: str, password: str) -> Any | None:
        """Return user if credentials are valid."""
        user = await self.adapter.get_or_none(self.user_model, username=username)
        if (
            not user
            or not getattr(user, "is_active", False)
            or not getattr(user, "is_staff", False)
            or not await password_hasher.check_password(password, user.password)
        ):
            return None
        return user

    async def superuser_exists(self) -> bool:
        """Check if a superuser already exists."""
        queryset = self.adapter.filter(
            self.user_model,
            is_staff=True,
            is_superuser=True,
        )
        return await self.adapter.exists(queryset)

    async def create_superuser(self, username: str, email: str, password: str) -> Any:
        """Create a new superuser."""
        return await self.adapter.create(
            self.user_model,
            username=username,
            email=email,
            password=await password_hasher.make_password(password),
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

# The End

