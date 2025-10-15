# -*- coding: utf-8 -*-
"""
delete_selected

Delete selected action implementation.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Dict, List

from . import ActionResult, ActionSpec, BaseAction
from ..services.permissions import PermAction
from freeadmin.core.boot import admin as boot_admin


class DeleteSelectedAction(BaseAction):
    """Delete selected objects from a list."""

    spec = ActionSpec(
        name="delete_selected",
        label="Delete selected",
        description="Delete selected objects.",
        danger=True,
        scope=["ids", "query"],
        params_schema={"confirm": bool},  # exposed to clients as "boolean"
        required_perm=PermAction.delete,
    )

    async def run(self, qs: List[Any], params: Dict[str, Any], user: Any) -> ActionResult:
        if params.get("confirm") is not True:
            return ActionResult(ok=False, errors=["Operation not confirmed."])

        affected = 0
        skipped = 0
        errors: List[str] = []

        for obj in qs:
            if not self._user_has_perm(user, getattr(self.spec, "required_perm", None)):
                skipped += 1
                errors.append(f"Permission denied for {obj!r}")
                continue
            try:
                await boot_admin.adapter.delete(obj)
                affected += 1
            except Exception as exc:  # pragma: no cover - safe deletion
                skipped += 1
                errors.append(str(exc))

        ok = not errors
        return ActionResult(ok=ok, affected=affected, skipped=skipped, errors=errors)


__all__ = ["DeleteSelectedAction"]

# The End

