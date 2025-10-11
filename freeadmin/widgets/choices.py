# -*- coding: utf-8 -*-
"""Choices Widgets

Choices.js based multi-select widget.
Custom widget for rendering selectable choices in Django forms.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com

Configuration is driven by ``FieldDescriptor.meta``. Only fields backed by a
many-to-many relation render as a multi-select array; all other fields produce
a single value.

``meta["choices_map"]`` supplies value/label pairs. Additional settings for
`Choices.js <https://github.com/Choices-js/Choices>`_ are accepted via
``meta["choices_options"]`` and merged with the default
``{"removeItemButton": True}``. Common options include ``allowSearch`` or
``maxItemCount``. A ``placeholder`` entry populates the empty option text in
JSONEditor.
"""

from __future__ import annotations

from typing import Any
from .base import BaseWidget
from .mixins import (
    RelationChoicesMixin,
    RelationPrefetchMixin,
    RelationValueMixin,
)
from .registry import registry


@registry.register("choices")
class ChoicesWidget(
    RelationChoicesMixin, RelationPrefetchMixin, RelationValueMixin, BaseWidget
):
    """Multi-select widget powered by Choices.js.

    The widget emits JSONEditor fields using ``format="choices"``. It switches
    to an array schema when the field accepts multiple values and otherwise
    returns a single string. ``FieldDescriptor.meta`` can define
    ``choices_map`` for the available options, an optional ``placeholder`` for
    empty selections, and ``choices_options`` with extra parameters passed to
    Choices.js (e.g. ``allowSearch`` or ``maxItemCount``).
    """

    assets_js = (
        "https://cdn.jsdelivr.net/npm/choices.js/public/assets/scripts/choices.min.js",
        "/static/widgets/choices.js",
    )

    class Media:
        css = (
            "https://cdn.jsdelivr.net/npm/choices.js/public/assets/styles/choices.min.css",
        )
        js = (
            "https://cdn.jsdelivr.net/npm/choices.js/public/assets/scripts/choices.min.js",
            "/static/widgets/choices.js",
        )

    Meta = Media

    @property
    def empty_many_value(self) -> list[str]:
        """Return the default empty value for multi-select fields."""

        return []

    def _choices_from_fd(self) -> dict[str, str]:
        """Return a mapping of option values to their labels."""

        field = self.ctx.field if self.ctx else None
        meta = getattr(field, "meta", {}) if field else {}
        had_meta = bool(field and hasattr(field, "meta"))
        choices_map = meta.get("choices_map") if meta else None
        if isinstance(choices_map, dict) and choices_map:
            return dict(choices_map)
        if field is None:
            return {}
        choices = getattr(field, "choices", None)
        relation = getattr(field, "relation", None)
        generated = self.ensure_choices_map(field)
        if not had_meta and not relation and choices:
            try:
                object.__delattr__(field, "meta")
            except AttributeError:
                pass
        return dict(generated)

    def get_startval(self) -> Any:
        """Return the initial form value, normalizing empty singles to blank strings."""

        value = super().get_startval()
        if self.is_many:
            return value
        if value is None:
            field = self.ctx.field if self.ctx else None
            required = bool(getattr(field, "required", False))
            return "" if not required else None
        return value

    @property
    def is_many(self) -> bool:
        """Return ``True`` only when the field has an M2M relation."""
        fd = self.ctx.field if self.ctx else None
        rel = getattr(fd, "relation", None)
        return bool(rel and getattr(rel, "kind", "") == "m2m")

    def get_schema(self) -> dict[str, Any]:
        """Build and return a JSON schema describing the field's choices."""
        fd = self.ctx.field
        meta = getattr(fd, "meta", {})
        choices_defaults: dict[str, Any] = {"removeItemButton": True}
        choices_opts = {**choices_defaults, **meta.get("choices_options", {})}

        choices_map = self._choices_from_fd()
        enum = list(choices_map.keys())
        titles = list(choices_map.values())
        options: dict[str, Any] = {"choices_options": choices_opts}
        if "placeholder" in meta:
            options["placeholder"] = meta["placeholder"]

        if self.is_many:
            item_options: dict[str, Any] = {"enum_titles": titles}
            schema = {
                "type": "array",
                "title": self.get_title(),
                "format": "choices",
                "uniqueItems": True,
                "items": {"type": "string", "enum": enum, "options": item_options},
                "options": options,
            }
            return self.merge_readonly(schema)

        options["enum_titles"] = titles
        schema = {
            "type": "string",
            "title": self.get_title(),
            "format": "choices",
            "enum": enum,
            "options": options,
        }
        return self.merge_readonly(schema)


# The End

