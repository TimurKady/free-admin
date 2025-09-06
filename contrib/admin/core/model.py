# -*- coding: utf-8 -*-
"""
model

ModelAdmin implementation.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any

from .base import BaseModelAdmin
from .inline import InlineModelAdmin


class ModelAdmin(BaseModelAdmin):
    """ORM Model Admin Class."""

    # IMPORTANT: use a tuple + forward-link string;
    # It's the most trouble-free option at runtime
    inlines: tuple[type["InlineModelAdmin"], ...] = ()

    def get_inlines(self) -> tuple[type["InlineModelAdmin"], ...]:
        """Return inline admin classes configured for this model."""
        return self.inlines

    async def get_inlines_spec(
        self, request: Any, user: Any, obj: Any | None = None
    ) -> list[dict[str, Any]]:
        """Return specification dictionaries for configured inlines."""
        specs: list[dict[str, Any]] = []
        for inline_cls in self.get_inlines():
            inline = inline_cls(inline_cls.model, self.adapter)
            md = self.adapter.get_model_descriptor(inline.model)
            setattr(inline, "app_label", getattr(inline, "app_label", md.app_label))
            columns = list(inline.get_list_columns(md))
            count = 0
            if obj is not None and getattr(inline, "parent_fk_name", None):
                pk_attr = self.adapter.get_pk_attr(self.model)
                pk_val = getattr(obj, pk_attr)
                qs = self.adapter.filter(
                    inline.model, **{inline.parent_fk_name: pk_val}
                )
                count = await self.adapter.count(qs)
            specs.append(
                {
                    "label": inline.get_label() or inline.get_verbose_name_plural(),
                    "app": getattr(inline, "app_label", md.app_label),
                    "model": getattr(
                        inline,
                        "model_slug",
                        md.model_name.lower(),
                    ),
                    "parent_fk": getattr(inline, "parent_fk_name", ""),
                    "can_add": inline.allow(user, "add", obj),
                    "can_delete": inline.can_delete and inline.allow(user, "delete", obj),
                    "collapsed": getattr(inline, "collapsed", True),
                    "columns": columns,
                    "columns_meta": inline.columns_meta(md, columns),
                    "count": count,
                }
            )
        return specs


# The End

