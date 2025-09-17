# -*- coding: utf-8 -*-
"""
tokens

Service for signing and verifying action scope tokens.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from config.settings import settings


class ScopeTokenService:
    """Sign and verify scope payloads with expiration."""

    def __init__(self, secret: str | None = None, algorithm: str = "HS256") -> None:
        """Initialize service with signing ``secret`` and ``algorithm``."""
        self._secret = secret or settings.JWT_SECRET_KEY
        self._algorithm = algorithm

    def sign(self, scope: Dict[str, Any], ttl: int) -> str:
        """Return a signed token encoding ``scope`` valid for ``ttl`` seconds."""
        payload = {
            "scope": scope,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=int(ttl)),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify(self, token: str) -> Dict[str, Any]:
        """Return decoded ``scope`` from ``token`` if valid and not expired."""
        try:
            data = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:  # pragma: no cover - explicit
            raise ValueError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:  # pragma: no cover - explicit
            raise ValueError("Invalid token") from exc
        scope = data.get("scope")
        if scope is None:
            raise ValueError("Missing scope")
        return scope

# The End

