# -*- coding: utf-8 -*-
"""
registry

Registry for admin pages and view entries.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Tuple, Type

from .pages import AdminPage
from .settings import SettingsKey, system_config
from .virtual import VirtualContentKey, VirtualContentNamer, VirtualContentRegistry


@dataclass(frozen=True)
class ViewEntry:
    """Registry entry describing a model admin."""

    app: str
    model: str
    admin_cls: Type
    settings: bool
    icon: str | None
    name: str | None


@dataclass(frozen=True)
class MenuItem:
    """Navigation menu item."""

    title: str
    path: str
    icon: str | None = None
    page_type: str | None = None


@dataclass(frozen=True)
class UserMenuItem:
    """User menu item."""

    title: str
    path: str
    icon: str | None = None


@dataclass(frozen=True)
class CardEntry:
    """Card descriptor used by the admin site."""

    key: str
    app: str
    app_slug: str
    title: str
    template: str
    icon: str | None = None
    channel: str | None = None
    col_class: str = "col-2"
    scripts: Tuple[str, ...] = field(default_factory=tuple)
    styles: Tuple[str, ...] = field(default_factory=tuple)
    slug: str = ""
    dotted: str = ""


class PageRegistry:
    """Store registered pages and model admin view entries."""

    def __init__(self) -> None:
        """Initialize empty collections for pages, views, and cards."""

        self.page_list: List[AdminPage] = []
        self.view_entries: List[ViewEntry] = []
        self.card_entries: Dict[str, CardEntry] = {}
        self._namer = VirtualContentNamer()
        self.virtual_registry = VirtualContentRegistry(self._namer)
        self._card_virtual: Dict[str, VirtualContentKey] = {}
        self._view_virtual_by_path: Dict[str, VirtualContentKey] = {}
        self._view_virtual_by_slug: Dict[tuple[str, str], VirtualContentKey] = {}
        self._registry_version: int = 0

    @property
    def registry_version(self) -> int:
        """Return the current monotonic registry version."""

        return self._registry_version

    def bump_version(self) -> None:
        """Advance the registry version to invalidate dependent caches."""

        self._registry_version += 1

    def register_page(self, page: AdminPage) -> None:
        """Add ``page`` to the registry without mutating menu state."""

        self.page_list.append(page)

    # View entries -----------------------------------------------------
    def register_view_entry(
        self,
        *,
        app: str,
        model: str,
        admin_cls: Type,
        settings: bool = False,
        icon: str | None = None,
        name: str | None = None,
    ) -> None:
        """Register a :class:`ViewEntry` for the given admin class.

        The operation is idempotent for the tuple ``(app, model, settings)`` and
        raises ``ValueError`` when the resulting path is already occupied by
        another page or view entry.
        """

        key = (app.lower(), model.lower(), settings)
        for e in self.view_entries:
            if (e.app.lower(), e.model.lower(), e.settings) == key:
                return  # Idempotent

        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")
        prefix = (
            f"{settings_prefix}/{app}/{model}" if settings else f"{orm_prefix}/{app}/{model}"
        )

        for e in self.view_entries:
            other_prefix = (
                f"{settings_prefix}/{e.app}/{e.model}"
                if e.settings
                else f"{orm_prefix}/{e.app}/{e.model}"
            )
            if other_prefix == prefix:
                raise ValueError(f"Path conflict: {prefix}")

        for page in self.page_list:
            if page.path == prefix:
                raise ValueError(f"Path conflict: {prefix}")

        entry = ViewEntry(
            app=app,
            model=model,
            admin_cls=admin_cls,
            settings=settings,
            icon=icon,
            name=name,
        )
        self.view_entries.append(entry)
        self.bump_version()

    def iter_orm(self) -> Iterator[ViewEntry]:
        """Iterate over non-settings admin registrations."""

        yield from (e for e in self.view_entries if not e.settings)

    def iter_settings(self) -> Iterator[ViewEntry]:
        """Iterate over settings admin registrations."""

        yield from (e for e in self.view_entries if e.settings)

    # Cards ------------------------------------------------------------
    def register_card(
        self,
        key: str,
        app: str,
        title: str,
        template: str,
        icon: str | None = None,
        channel: str | None = None,
        col_class: str = "col-2",
        *,
        scripts: List[str] | Tuple[str, ...] | None = None,
        styles: List[str] | Tuple[str, ...] | None = None,
    ) -> None:
        """Register a card while enforcing idempotency.

        ``scripts`` and ``styles`` store additional asset requirements for the
        card template and are preserved for template aggregation. ``col_class``
        stores the Bootstrap column classes applied on the dashboard grid.
        """

        existing = self.card_entries.get(key)
        if existing is not None:
            candidate = CardEntry(
                key=key,
                app=app,
                app_slug=existing.app_slug,
                title=title,
                template=template,
                icon=icon,
                channel=channel,
                col_class=col_class,
                scripts=tuple(scripts or ()),
                styles=tuple(styles or ()),
                slug=existing.slug,
                dotted=existing.dotted,
            )
            if existing != candidate:
                raise ValueError(
                    f"Card '{key}' is already registered with different data"
                )
            return

        virtual = self.virtual_registry.register(
            app_label=app,
            kind="cards",
            key=key,
            identifier=key,
        )

        entry = CardEntry(
            key=key,
            app=app,
            app_slug=virtual.app_slug,
            title=title,
            template=template,
            icon=icon,
            channel=channel,
            col_class=col_class,
            scripts=tuple(scripts or ()),
            styles=tuple(styles or ()),
            slug=virtual.slug,
            dotted=virtual.dotted,
        )
        self.card_entries[key] = entry
        self._card_virtual[key] = virtual

    def get_card_virtual(self, key: str) -> VirtualContentKey | None:
        """Return the virtual metadata registered for ``key``."""

        return self._card_virtual.get(key)

    def iter_virtual_cards(self) -> Iterator[VirtualContentKey]:
        """Iterate over virtual entries associated with cards."""

        yield from self._card_virtual.values()

    def register_view_virtual(
        self,
        *,
        path: str,
        app_label: str,
        slug_source: str,
    ) -> VirtualContentKey:
        """Register virtual metadata for ``path`` and return it."""

        normalized_path = path.rstrip("/") or "/"
        existing = self._view_virtual_by_path.get(normalized_path)
        desired_app_slug = self._namer.slugify(app_label)
        desired_slug = self._namer.slugify(slug_source)
        if not desired_app_slug:
            raise ValueError("App label must not be empty for views")
        if not desired_slug:
            raise ValueError("Slug source must not be empty for views")
        if existing is not None:
            if (
                existing.app_slug != desired_app_slug
                or existing.slug != desired_slug
            ):
                raise ValueError(
                    f"View '{normalized_path}' already registered with different metadata"
                )
            return existing

        virtual = self.virtual_registry.register(
            app_label=app_label,
            kind="views",
            key=slug_source,
            identifier=normalized_path,
        )
        self._view_virtual_by_path[normalized_path] = virtual
        self._view_virtual_by_slug[(virtual.app_slug, virtual.slug)] = virtual
        return virtual

    def get_view_virtual_by_path(self, path: str) -> VirtualContentKey | None:
        """Return virtual metadata previously stored for ``path``."""

        normalized_path = path.rstrip("/") or "/"
        return self._view_virtual_by_path.get(normalized_path)

    def get_view_virtual(self, app_slug: str, slug: str) -> VirtualContentKey | None:
        """Return virtual metadata identified by ``app_slug`` and ``slug``."""

        return self._view_virtual_by_slug.get((app_slug.lower(), slug))

    def iter_virtual_views(self) -> Iterator[VirtualContentKey]:
        """Iterate over all registered virtual views."""

        yield from self.virtual_registry.iter_entries(kind="views")

    def get_card(self, key: str) -> CardEntry:
        """Return registered card by key or raise ``ValueError``."""

        entry = self.card_entries.get(key)
        if entry is None:
            raise ValueError(f"Unknown card: {key}")
        return entry

    def iter_cards(self) -> Iterator[CardEntry]:
        """Iterate over registered cards."""

        yield from self.card_entries.values()

# The End

