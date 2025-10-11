# -*- coding: utf-8 -*-
"""
registry

Registry for admin ORM adapters.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from .base import BaseAdapter


class AdapterRegistry:
    """Registry for admin ORM adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        """Register an adapter instance."""
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> BaseAdapter:
        """Return adapter by ``name``."""
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise ModuleNotFoundError(f"Adapter '{name}' not registered") from exc


registry = AdapterRegistry()

__all__ = ["AdapterRegistry", "registry"]

# The End

