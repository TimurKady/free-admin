# -*- coding: utf-8 -*-
"""
ORM

Illustrative ORM configuration for the FreeAdmin example project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations


class ExampleORMConfig:
    """Provide adapter wiring for the FreeAdmin example project."""

    def __init__(self, *, adapter_name: str = "tortoise", dsn: str | None = None) -> None:
        """Store adapter label and connection string."""

        self._adapter_name = adapter_name
        self._dsn = dsn or "sqlite://:memory:"

    @property
    def adapter_name(self) -> str:
        """Return the name of the ORM adapter in use."""

        return self._adapter_name

    @property
    def connection_dsn(self) -> str:
        """Return the DSN used for the default database connection."""

        return self._dsn

    def describe(self) -> dict[str, str]:
        """Return a human-readable summary of the ORM configuration."""

        return {"adapter": self._adapter_name, "dsn": self._dsn}


__all__ = ["ExampleORMConfig"]

# The End

