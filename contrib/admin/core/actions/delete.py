# -*- coding: utf-8 -*-
"""
delete

Delete action implementation.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Dict, List

from . import ActionResult, ActionSpec, BaseAction
from ..permissions import PermAction
from ...boot import admin as boot_admin


class DeleteAction(BaseAction):
    """Delete objects from a queryset."""

    spec = ActionSpec(
        name="delete",
        label="Delete",
        description="Remove selected objects.",
        danger=True,
        scope=["ids"],
        params_schema={},
        required_perm=PermAction.delete,
    )

    async def run(self, qs: Any, params: Dict[str, Any], user: Any) -> ActionResult:
        affected = 0
        skipped = 0
        errors: List[str] = []
        perm = getattr(self.spec, "required_perm", None)
        for obj in qs:
            if not self._user_has_perm(user, perm):
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

__all__ = ["DeleteAction"]

# The End

