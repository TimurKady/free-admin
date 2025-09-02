# -*- coding: utf-8 -*-
"""
builder

Scope query builder implementation.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from types import SimpleNamespace
from collections.abc import Mapping
from typing import Type, TypeVar, Generic, cast

from fastapi import HTTPException


QS = TypeVar("QS")


class ScopeQueryBuilder(Generic[QS]):
    """Build querysets for scope queries with validation."""

    def __init__(self, admin, md, user, queryset_type: Type[QS]) -> None:
        self.admin = admin
        self.md = md
        self.user = user
        self.queryset_type = queryset_type

    def build(self, query: dict) -> QS:
        search = query.get("search", "") or ""
        if not isinstance(search, str):
            search = str(search)

        order = query.get("order", "") or ""
        if not isinstance(order, str):
            order = str(order)

        filters = query.get("filters", {}) or {}
        if not isinstance(filters, Mapping):
            raise HTTPException(status_code=400, detail="Invalid filters")

        if search and not self.admin.get_search_fields(self.md):
            raise HTTPException(status_code=400, detail="Search not allowed")

        if order:
            ord_field = order[1:] if order.startswith("-") else order
            if ord_field not in self.admin.get_orderable_fields(self.md):
                raise HTTPException(status_code=400, detail="Invalid order field")

        filter_specs = {
            spec["name"]: set(spec.get("ops", []))
            for spec in self.admin.get_list_filters(self.md)
        }
        prefix = getattr(self.admin, "FILTER_PREFIX", "filter.")
        allowed_ops = getattr(self.admin, "FILTER_OPS", {})
        for key in filters.keys():
            if not key.startswith(prefix):
                raise HTTPException(status_code=400, detail="Invalid filter field")
            frag = key[len(prefix) :]
            parts = frag.split(".") if frag else []
            op_key = ""
            if parts and parts[-1] in allowed_ops:
                op_key = parts[-1]
                if op_key != "":
                    parts = parts[:-1]
            field_name = ".".join(parts)
            if field_name not in filter_specs:
                base_field = ".".join(parts[:-1]) if len(parts) > 1 else None
                if base_field and base_field in filter_specs:
                    raise HTTPException(status_code=400, detail="Invalid filter operator")
                raise HTTPException(status_code=400, detail="Invalid filter field")
            op = allowed_ops.get(op_key, "eq")
            if op not in filter_specs[field_name]:
                raise HTTPException(status_code=400, detail="Invalid filter operator")

        dummy_req = SimpleNamespace(query_params=filters)
        params = {"search": search, "order": order}
        qs = self.admin.get_list_queryset(dummy_req, self.user, self.md, params)
        return cast(QS, qs)


__all__ = ["ScopeQueryBuilder"]

# The End

