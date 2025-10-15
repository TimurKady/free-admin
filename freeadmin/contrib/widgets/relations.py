# -*- coding: utf-8 -*-
"""
relations

Simple select widget working with pre-calculated choices.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Dict

from .base import BaseWidget
from .mixins import RelationChoicesMixin, RelationPrefetchMixin, RelationValueMixin
from .registry import registry


@registry.register("relation")
class RelationsWidget(
    RelationChoicesMixin, RelationPrefetchMixin, RelationValueMixin, BaseWidget
):
    """Simple select based on enum/enum_titles."""


    def get_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for relation selects.

        Uses a checkbox array when multiple selections are allowed and
        annotates single-value relations with ``format="select"`` so the
        frontend renders a proper dropdown control.
        """

        fd = self.ctx.field
        title = self.get_title()
        rel = getattr(fd, "relation", None)
        is_many = bool(getattr(fd, "many", False) or (rel and getattr(rel, "kind", "") == "m2m"))
        required = bool(getattr(fd, "required", False))

        enum, titles, placeholder = self.build_choices(fd, is_many, required)

        if is_many:
            items = {
                "type": "string",
                "enum": enum,
                "options": {"enum_titles": titles},
            }
            schema: Dict[str, Any] = {
                "type": "array",
                "title": title,
                "format": "checkbox",
                "uniqueItems": True,
                "items": items,
            }
            if placeholder is not None:
                schema["options"] = {"placeholder": placeholder}
            return self.merge_readonly(schema)

        schema = {
            "type": "string",
            "title": title,
            "enum": enum,
            "format": "select",
        }
        options: Dict[str, Any] = {}
        if enum:
            options["enum_titles"] = titles or enum
        if placeholder is not None:
            options["placeholder"] = placeholder
        if options:
            schema["options"] = options
        return self.merge_readonly(schema)

    # get_startval and to_storage are provided by RelationValueMixin

# The End

