# -*- coding: utf-8 -*-
"""
model

ModelAdmin implementation.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Sequence

from .base import BaseModelAdmin
from .inline import InlineModelAdmin


class ModelAdmin(BaseModelAdmin):
    """ORM Model Admin Class."""

    # IMPORTANT: use a tuple + forward-link string
    # It's the most trouble-free option at runtime
    inlines: tuple[type["InlineModelAdmin"], ...] = ()

    # Data exchange capabilities
    export_formats: Sequence[str] = ("json",)
    export_filename_template: str = "{app}_{model}_{timestamp}.{fmt}"
    import_strict: bool = True

    def get_inlines(self) -> tuple[type["InlineModelAdmin"], ...]:
        """Return inline admin classes configured for this model."""
        return self.inlines

    def get_import_lookup_fields(self) -> list[str]:
        """Return unique fields used to lookup objects during import."""
        md = self.adapter.get_model_descriptor(self.model)
        return [f.name for f in md.fields if f.unique]

    async def get_or_create_for_import(
        self, data: dict[str, Any]
    ) -> tuple[Any, bool]:
        """Return existing object or create a new one for import.

        Unique fields provided in the incoming ``data`` are used to look up
        existing objects. If an object matching all available unique fields is
        found, it is returned with ``created`` set to ``False``. Otherwise a new
        object is created and returned with ``created`` set to ``True``.
        """
        data = self.adapter.normalize_import_data(self.model, data)
        lookup_fields = self.get_import_lookup_fields()
        filters = {field: data[field] for field in lookup_fields if field in data}
        if filters:
            obj = await self.adapter.get_or_none(self.model, **filters)
            if obj is not None:
                return obj, False
        obj = await self.adapter.create(self.model, **data)
        return obj, True

    async def update_for_import(self, obj: Any, data: dict[str, Any]) -> None:
        """Update an existing object with imported ``data``.

        The base implementation simply assigns provided values and saves the
        object using the adapter.
        """
        self.adapter.assign(obj, data)
        await self.adapter.save(obj)

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
                    "label": inline.get_model_label() or inline.get_verbose_name_plural(),
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

    def can_export(self, user: Any) -> bool:
        return self._user_has_perm(user, self.perm_export)

    def can_import(self, user: Any) -> bool:
        return self._user_has_perm(user, self.perm_import)

    def allow(self, user: Any, action: str, obj: Any | None = None) -> bool:
        if action == "export":
            return self.can_export(user)
        if action == "import":
            return self.can_import(user)
        return super().allow(user, action, obj)


# The End

