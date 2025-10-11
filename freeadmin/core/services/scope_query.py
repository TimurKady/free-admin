# -*- coding: utf-8 -*-
"""
scope_query

Service for building querysets based on scope payloads.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from ...adapters import BaseAdapter
from .auth import AdminUserDTO
from ..actions.builder import ScopeQueryBuilder
from ..filters import FilterSpec


class ScopeQueryService:
    """Build querysets from scope definitions."""

    def __init__(self, adapter: BaseAdapter | None = None) -> None:
        """Initialize the service with an optional adapter."""
        from ...boot import admin as boot_admin

        self.adapter = adapter or boot_admin.adapter

    def build_queryset(
        self,
        admin,
        md,
        request: Request,
        user: AdminUserDTO,
        scope: dict,
    ):
        """Build a queryset according to the provided scope definition."""
        qs = admin.get_objects(request, user)
        if not isinstance(scope, dict):
            raise HTTPException(status_code=400, detail="Invalid scope format")
        if not scope or "type" not in scope:
            raise HTTPException(status_code=400, detail="Missing scope.type")

        scope_type = scope["type"]
        if scope_type == "ids":
            ids = scope.get("ids")
            if ids is None:
                raise HTTPException(status_code=400, detail="Missing scope.ids")
            qs = self.adapter.apply_filter_spec(
                qs, [FilterSpec(md.pk_attr, "in", ids)]
            )
        elif scope_type == "query":
            query = scope.get("query")
            if query is None:
                raise HTTPException(status_code=400, detail="Missing scope.query")
            builder = ScopeQueryBuilder(admin, md, user, self.adapter.QuerySet)
            qs = builder.build(query)
        else:
            raise HTTPException(status_code=400, detail="Invalid scope.type")
        return qs


# The End

