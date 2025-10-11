# -*- coding: utf-8 -*-
"""
export_selected

Export selected action implementation.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Dict, List

from . import ActionResult, ActionSpec, BaseAction
from ..services.permissions import PermAction


class ExportSelectedAction(BaseAction):
    """Export selected objects from a list."""

    cache_backend: Any | None = None

    spec = ActionSpec(
        name="export_selected",
        label="Export selected",
        description="Export selected objects.",
        danger=False,
        scope=["ids", "query"],
        params_schema={"fields": list[str], "fmt": str},
        required_perm=PermAction.export,
    )

    async def run(self, qs: List[Any], params: Dict[str, Any], user: Any) -> ActionResult:
        allowed = list(self.admin.get_export_fields()) if self.admin else []
        fields = [f for f in params.get("fields", allowed) if f in allowed]
        fmt = params.get("fmt", "json")
        if not fields:
            return ActionResult(ok=False, errors=["No fields specified."])
        from ..services.export import ExportService

        adapter = self.admin.adapter
        md = adapter.get_model_descriptor(self.admin.model)
        pk_attr = getattr(md, "pk_attr", "id")
        ids = [getattr(obj, pk_attr) for obj in qs]
        queryset = adapter.filter(self.admin.model, **{f"{pk_attr}__in": ids})
        service = ExportService(adapter, cache_backend=self.cache_backend)
        token = await service.run(
            queryset, fields, fmt, model_name=self.admin.model.__name__
        )
        return ActionResult(ok=True, affected=len(ids), report=token)


__all__ = ["ExportSelectedAction"]

# The End

