# -*- coding: utf-8 -*-
"""
virtual

Utilities for deterministic naming of virtual content types.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple


@dataclass(frozen=True)
class VirtualContentKey:
    """Represent a normalized identifier for a virtual content type."""

    app_label: str
    app_slug: str
    kind: str
    key: str
    slug: str
    dotted: str


class VirtualContentNamer:
    """Normalize labels and build deterministic dotted identifiers."""

    _slug_re = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

    def slugify(self, value: str) -> str:
        """Return a lower-case slug derived from ``value``."""

        normalized = value.strip()
        if not normalized:
            return ""
        lowered = normalized.lower()
        slug = self._slug_re.sub("-", lowered).strip("-")
        return slug

    def make_dotted(self, app: str, kind: str, key: str) -> str:
        """Return a dotted identifier for ``app.kind.key``."""

        app_slug = self.slugify(app)
        key_slug = self.slugify(key)
        if not app_slug or not key_slug:
            raise ValueError("App and key must produce non-empty slugs")
        return f"{app_slug}.{kind}.{key_slug}"


class VirtualContentRegistry:
    """Track slug usage and resolve dotted names for virtual entries."""

    def __init__(self, namer: VirtualContentNamer | None = None) -> None:
        """Initialize storage for slug uniqueness tracking."""

        self._namer = namer or VirtualContentNamer()
        self._by_dotted: Dict[str, VirtualContentKey] = {}
        self._by_kind_slug: Dict[Tuple[str, str, str], VirtualContentKey] = {}
        self._by_identifier: Dict[Tuple[str, str], VirtualContentKey] = {}

    def register(
        self,
        *,
        app_label: str,
        kind: str,
        key: str,
        identifier: str,
    ) -> VirtualContentKey:
        """Register a virtual entry for ``app_label`` and ``key``."""

        app_slug = self._namer.slugify(app_label)
        slug = self._namer.slugify(key)
        if not app_slug:
            raise ValueError("App label must not be empty")
        if not slug:
            raise ValueError("Slug key must not be empty")
        unique_key = (app_slug, kind, slug)
        if unique_key in self._by_kind_slug:
            raise ValueError(
                f"Duplicate {kind} slug '{slug}' detected for app '{app_slug}'"
            )
        dotted = f"{app_slug}.{kind}.{slug}"
        entry = VirtualContentKey(
            app_label=app_label,
            app_slug=app_slug,
            kind=kind,
            key=key,
            slug=slug,
            dotted=dotted,
        )
        self._by_kind_slug[unique_key] = entry
        self._by_dotted[dotted] = entry
        self._by_identifier[(kind, identifier)] = entry
        return entry

    def unregister(self, *, kind: str, identifier: str) -> None:
        """Remove the registered entry associated with ``identifier``."""

        entry = self._by_identifier.pop((kind, identifier), None)
        if entry is None:
            return
        unique_key = (entry.app_slug, entry.kind, entry.slug)
        self._by_kind_slug.pop(unique_key, None)
        self._by_dotted.pop(entry.dotted, None)

    def get_by_dotted(self, dotted: str) -> VirtualContentKey | None:
        """Return the entry associated with ``dotted`` if registered."""

        return self._by_dotted.get(dotted)

    def get_by_identifier(self, kind: str, identifier: str) -> VirtualContentKey | None:
        """Return the entry registered under ``identifier`` and ``kind``."""

        return self._by_identifier.get((kind, identifier))

    def iter_entries(self, *, kind: str | None = None) -> Iterable[VirtualContentKey]:
        """Yield registered entries filtered by ``kind`` when provided."""

        values = self._by_dotted.values()
        if kind is None:
            yield from values
            return
        for entry in values:
            if entry.kind == kind:
                yield entry


__all__ = [
    "VirtualContentKey",
    "VirtualContentNamer",
    "VirtualContentRegistry",
]

# The End

