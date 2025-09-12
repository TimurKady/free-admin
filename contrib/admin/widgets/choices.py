# -*- coding: utf-8 -*-
"""Choices Widgets

Choices.js based multi-select widget.
Custom widget for rendering selectable choices in Django forms.

Version: 0.1.0
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
from .registry import registry


@registry.register("choices")
class ChoicesWidget(BaseWidget):
    """Multi-select widget powered by Choices.js.

    The widget emits JSONEditor fields using ``format="choices"``. It switches
    to an array schema when the field accepts multiple values and otherwise
    returns a single string. ``FieldDescriptor.meta`` can define
    ``choices_map`` for the available options, an optional ``placeholder`` for
    empty selections, and ``choices_options`` with extra parameters passed to
    Choices.js (e.g. ``allowSearch`` or ``maxItemCount``).
    """

    class Media:
        css = (
            "https://cdn.jsdelivr.net/npm/choices.js/public/assets/styles/choices.min.css",
        )
        js = (
            "https://cdn.jsdelivr.net/npm/choices.js/public/assets/scripts/choices.min.js",
        )

    Meta = Media

    def _choices_from_fd(self) -> dict[str, str]:
        """Return a mapping of option values to their labels."""

        field = self.ctx.field if self.ctx else None
        meta = getattr(field, "meta", {}) if field else {}
        choices_map = dict(meta.get("choices_map", {}))
        if not choices_map and field is not None:
            for choice in getattr(field, "choices", []) or []:
                if isinstance(choice, (list, tuple)) and len(choice) >= 2:
                    key, label = choice[0], choice[1]
                else:
                    key = getattr(choice, "const", getattr(choice, "value", choice))
                    label = getattr(choice, "title", getattr(choice, "label", str(choice)))
                choices_map[str(key)] = str(label)
        return choices_map

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
            schema = {
                "type": "array",
                "title": self.get_title(),
                "format": "choices",
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": enum,
                    "options": {"enum_titles": titles},
                },
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

    def get_startval(self) -> Any:
        """Return the widget's initial value as list, string, or None."""
        if not self.ctx:
            return None

        fd = self.ctx.field
        required = bool(getattr(fd, "required", False))
        default = getattr(fd, "default", None)

        inst = self.ctx.instance
        if inst is None:
            start = default if default is not None else (None if required else ([] if self.is_many else ""))
        else:
            start = getattr(inst, self.ctx.name, None)
            if start is None:
                start = default if default is not None else (None if required else ([] if self.is_many else ""))

        if self.is_many:
            if self.ctx.instance is not None:
                ids = getattr(self.ctx.instance, f"{self.ctx.name}_ids", None)
                if ids is not None:
                    start = ids
            if start is None:
                return []
            if not isinstance(start, (list, tuple, set)):
                start = [start]
            return [str(v) for v in start]

        if start in (None, ""):
            return start
        return str(start)

    def to_storage(self, value: Any, options: dict[str, Any] | None = None) -> Any:
        """Normalize submitted data into a storage-friendly list, string, or None."""
        if value is None:
            return [] if self.is_many else None

        if self.is_many:
            if not isinstance(value, (list, tuple)):
                value = [value]
            return [str(v) for v in value]

        return str(value)

# The End

