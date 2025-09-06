# -*- coding: utf-8 -*-
"""
relations

Simple select widget working with pre-calculated choices.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Dict

from ..boot import admin as boot_admin
from .base import BaseWidget
from .registry import registry

_ = boot_admin.adapter


@registry.register("relation")
class RelationsWidget(BaseWidget):
    """Simple select based on enum/enum_titles."""

    def _choices_from_fd(self, fd) -> tuple[list[str], list[str]]:
        """Extract ``enum`` and ``titles`` from a field descriptor.

        Some ``FieldDescriptor`` instances might not have the ``meta`` attribute
        populated (e.g. when ``prefetch`` was not executed or the field does not
        require additional metadata).  Accessing ``fd.meta`` directly in those
        cases raises ``AttributeError`` which breaks schema generation.  To make
        the widget more robust we gracefully handle missing ``meta`` and simply
        return empty choices.
        """

        meta = getattr(fd, "meta", None) or {}
        cm = meta.get("choices_map")
        if not cm and getattr(fd, "relation", None) is None and getattr(fd, "choices", None):
            cm = {}
            for ch in fd.choices:
                key = getattr(ch, "const", getattr(ch, "value", ch))
                label = getattr(ch, "title", getattr(ch, "label", str(ch)))
                cm[str(key)] = str(label)
            meta["choices_map"] = cm
            object.__setattr__(fd, "meta", meta)
        elif not cm:
            cm = {}
        enum = list(cm.keys())
        titles = list(cm.values())
        return enum, titles

    async def prefetch(self) -> None:
        fd = self.ctx.field
        rel = getattr(fd, "relation", None)
        if not rel:
            return

        RelModel = boot_admin.adapter.get_model(rel.target)
        if RelModel is None:
            return

        pk_attr = boot_admin.adapter.get_pk_attr(RelModel)
        qs = boot_admin.adapter.all(RelModel)
        qs = boot_admin.adapter.order_by(qs, pk_attr)
        objs = await boot_admin.adapter.fetch_all(qs)
        choices_map = {str(getattr(o, pk_attr)): str(o) for o in objs}

        meta = dict(getattr(fd, "meta", {}) or {})
        meta["choices_map"] = choices_map
        object.__setattr__(fd, "meta", meta)

        inst = self.ctx.instance
        if getattr(rel, "kind", "") == "m2m" and inst is not None:
            await boot_admin.adapter.fetch_related(inst, self.ctx.name)
            related = getattr(inst, self.ctx.name) or []
            ids = [getattr(o, pk_attr) for o in sorted(related, key=lambda o: getattr(o, pk_attr))]
            setattr(inst, f"{self.ctx.name}_ids", ids)

        if inst is not None:
            cur = getattr(inst, f"{self.ctx.name}_id", None)
            if cur is not None:
                key = str(cur)
                if key not in choices_map:
                    try:
                        obj = await boot_admin.adapter.get(RelModel, **{pk_attr: cur})
                        choices_map[key] = str(obj)
                    except Exception:
                        choices_map[key] = key
                meta["current_label"] = choices_map.get(key)
                object.__setattr__(fd, "meta", meta)

    def get_schema(self) -> Dict[str, Any]:
        fd = self.ctx.field
        title = self.get_title()
        rel = getattr(fd, "relation", None)
        is_many = bool(getattr(fd, "many", False) or (rel and getattr(rel, "kind", "") == "m2m"))
        required = bool(getattr(fd, "required", False))

        enum, titles = self._choices_from_fd(fd)

        # Placeholder: only for single selects and only if the field is optional
        if not required and not is_many:
            if not enum or enum[0] != "":
                enum = [""] + enum
                titles = ["--- Select ---"] + titles

        if is_many:
            schema = {
                "type": "array",
                "title": title,
                "format": "select",
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": enum,
                    "options": {"enum_titles": titles},
                },
            }
            return self.merge_readonly(schema)

        schema = {
            "type": "string",
            "title": title,
            "enum": enum,
            "options": {"enum_titles": titles},
        }
        return self.merge_readonly(schema)

    def get_startval(self) -> Any:
        fd = self.ctx.field
        rel = getattr(fd, "relation", None)
        is_many = bool(getattr(fd, "many", False) or (rel and getattr(rel, "kind", "") == "m2m"))
        required = bool(getattr(fd, "required", False))

        # add
        if self.ctx.instance is None:
            # For single selects, explicitly include an empty value
            if not required and not is_many:
                return ""
            return None

        # edit: FK → "<pk>", M2M → ["<pk>", ...]
        if rel:
            if is_many:
                ids = getattr(self.ctx.instance, f"{self.ctx.name}_ids", None)
                return [str(v) for v in ids] if ids is not None else []
            cur = getattr(self.ctx.instance, f"{self.ctx.name}_id", None)
            return "" if (cur is None and not required) else (str(cur) if cur is not None else None)

        # simple fields
        return getattr(self.ctx.instance, self.ctx.name, None)

    def to_storage(self, value: Any, options: Dict[str, Any] | None = None) -> Any:
        if value is None:
            return None
        fd = self.ctx.field
        rel = getattr(fd, "relation", None)
        is_many = bool(getattr(fd, "many", False) or (rel and getattr(rel, "kind", "") == "m2m"))
        if is_many:
            return [str(v) for v in value]
        return str(value)

# The End

