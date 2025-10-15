# -*- coding: utf-8 -*-
"""
mixins

Utility mixins for admin widgets.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

# admin/widgets/mixins.py
from __future__ import annotations

import inspect

from typing import Any, Dict, Iterable

from ...core.boot import admin as boot_admin


class RelationChoicesMixin:
    """Provide helpers for deriving enum choices from metadata."""

    def ensure_choices_map(self, fd: Any) -> dict[str, str]:
        """Populate ``fd.meta['choices_map']`` from ``fd.choices`` when missing.

        Args:
            fd: Field descriptor potentially carrying static ``choices``.

        Returns:
            Mapping of choice values to labels as strings.
        """
        meta = getattr(fd, "meta", None) or {}
        if meta.get("choices_map"):
            return meta["choices_map"]

        choices_map: dict[str, str] = {}
        for choice in getattr(fd, "choices", []) or []:
            if isinstance(choice, (list, tuple)) and len(choice) >= 2:
                key, label = choice[0], choice[1]
            else:
                key = getattr(choice, "const", getattr(choice, "value", choice))
                label = getattr(choice, "title", getattr(choice, "label", str(choice)))
            choices_map[str(key)] = str(label)

        meta["choices_map"] = choices_map
        object.__setattr__(fd, "meta", meta)
        return choices_map

    def build_choices(
        self, fd: Any, is_many: bool, required: bool
    ) -> tuple[list[str], list[str], str]:
        """Form ``enum`` and ``enum_titles`` from a field's ``choices_map``.

        A placeholder label is always returned. Required fields use an empty
        placeholder while optional fields use ``"--- Select ---"``. For optional
        singular fields with predefined choices, an empty option is prepended to
        enable clearing the selection. Array-based fields simply receive the
        placeholder without altering ``enum`` or ``titles``.

        Args:
            fd: Field descriptor possibly containing ``meta['choices_map']``.
            is_many: Indicates if multiple selections are allowed.
            required: Indicates if the field is mandatory.

        Returns:
            Tuple of ``(enum, titles, placeholder)`` where ``enum`` and
            ``titles`` are lists of strings and ``placeholder`` is always the
            default label for an empty selection.
        """
        choices_map = self.ensure_choices_map(fd)
        enum = list(choices_map.keys())
        titles = list(choices_map.values())
        placeholder = "" if required else "--- Select ---"

        if not is_many and not required and enum:
            enum.insert(0, "")
            titles.insert(0, placeholder)

        return enum, titles, placeholder


class RelationPrefetchMixin:
    """Prefetch relation choices and populate field metadata."""

    prefetch_requires_instance: bool = False

    async def prefetch(self) -> None:
        """Load available relation choices and current labels.

        When ``prefetch_requires_instance`` is ``True``, the prefetch routine
        executes only if ``ctx.instance`` is provided.
        """
        fd = self.ctx.field
        rel = getattr(fd, "relation", None)
        inst = self.ctx.instance
        if not rel or (self.prefetch_requires_instance and inst is None):
            return

        admin = boot_admin.get_admin(rel.target) or self.ctx.admin
        if admin is None:
            return

        pairs = await admin.get_choices(fd)
        choices_map = {pk: label for pk, label in pairs}

        meta = dict(getattr(fd, "meta", {}) or {})
        meta["choices_map"] = choices_map

        if inst is not None:
            if getattr(rel, "kind", "") == "m2m":
                ids = await self._resolve_many_to_many_ids(inst)
                setattr(inst, f"{self.ctx.name}_ids", ids)
            else:
                cur = getattr(inst, f"{self.ctx.name}_id", None)
                if cur is not None:
                    key = str(cur)
                    if key not in choices_map:
                        try:
                            obj = getattr(inst, self.ctx.name)
                        except Exception:
                            obj = None
                        choices_map[key] = (
                            admin.get_label(obj) if obj is not None else key
                        )
                    meta["current_label"] = choices_map.get(key)

        object.__setattr__(fd, "meta", meta)

    async def _resolve_many_to_many_ids(self, inst: Any) -> list[str]:
        """Collect many-to-many primary keys for the given instance."""
        ids: list[str] = []
        manager = getattr(inst, self.ctx.name, None)
        related: Iterable[Any] | None

        if manager is None:
            return ids

        if isinstance(manager, (list, tuple, set)):
            related = manager
        else:
            loader = getattr(manager, "all", None)
            related = None
            if callable(loader):
                try:
                    data = loader()
                    if inspect.isawaitable(data):
                        data = await data
                    related = data
                except Exception:
                    related = None
            if related is None:
                try:
                    related = list(manager)
                except TypeError:
                    related = None

        if not related:
            return ids

        for obj in related:
            if obj is None:
                continue
            pk = getattr(obj, "pk", getattr(obj, "id", obj))
            ids.append(str(pk))
        return ids


class RelationValueMixin:
    """Provide shared value handling for relation-based widgets."""

    empty_many_value: Any = None

    def get_startval(self) -> Any:
        """Determine initial form value for the field.

        Examines existing instance values first. When an instance does not
        supply a value, the field's ``default`` is inspected and returned as
        the initial selection, converted to string identifiers where
        appropriate.
        """
        fd = self.ctx.field
        rel = getattr(fd, "relation", None)
        is_many = bool(
            getattr(fd, "many", False) or (rel and getattr(rel, "kind", "") == "m2m")
        )
        required = bool(getattr(fd, "required", False))
        default = getattr(fd, "default", None)
        if callable(default):
            default = default()

        if self.ctx.instance is None:
            if default is not None:
                if is_many:
                    if isinstance(default, (list, tuple, set)):
                        return [str(v) for v in default]
                    return [str(default)]
                return str(default)
            if is_many:
                return self.empty_many_value
            return "" if not required else None

        if rel:
            if is_many:
                ids = getattr(self.ctx.instance, f"{self.ctx.name}_ids", None)
                if ids is not None:
                    return [str(v) for v in ids]
                if default is not None:
                    if isinstance(default, (list, tuple, set)):
                        return [str(v) for v in default]
                    return [str(default)]
                return []
            cur = getattr(self.ctx.instance, f"{self.ctx.name}_id", None)
            if cur is not None:
                return str(cur)
            if default is not None:
                return str(default)
            return "" if not required else None

        value = getattr(self.ctx.instance, self.ctx.name, None)
        if value is not None:
            return value
        if default is not None:
            return default
        return value

    def to_storage(self, value: Any, options: Dict[str, Any] | None = None) -> Any:
        """Convert submitted value into a storage-friendly format."""
        fd = self.ctx.field
        rel = getattr(fd, "relation", None)
        is_many = bool(
            getattr(fd, "many", False) or (rel and getattr(rel, "kind", "") == "m2m")
        )
        if value is None:
            return self.empty_many_value if is_many else None
        return [str(v) for v in value] if is_many else str(value)


# The End

