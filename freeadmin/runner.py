# -*- coding: utf-8 -*-
"""runner

Background runner for admin actions.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from types import SimpleNamespace

from .adapters import BaseAdapter
from .boot import admin as boot_admin
from .core.services.auth import AdminUserDTO
from .core.services import ScopeQueryService
from .core.exceptions import ActionNotFound


class AdminActionRunner:
    """Execute admin actions synchronously when background execution is unavailable."""

    def __init__(self, adapter: BaseAdapter | None = None) -> None:
        """Initialize the runner with an optional ORM ``adapter`` dependency."""

        self.adapter = adapter or boot_admin.adapter
        self.scope_query_service = ScopeQueryService(self.adapter)

    async def run(
        self,
        app: str,
        model: str,
        action: str,
        scope: dict,
        params: dict,
        user: AdminUserDTO,
        admin_site=None,
    ) -> dict:
        """Execute ``action`` immediately and return a serializable payload."""

        from .api import AdminAPI  # local import to avoid circular
        from .hub import admin_site as global_admin_site  # local import to avoid circular

        site = admin_site or global_admin_site
        admin = site.find_admin_or_404(app, model)
        action_obj = admin.get_action(action)
        if action_obj is None:
            raise ActionNotFound(f"Unknown action: {action}")
        params_validator = AdminAPI.ParamsValidator()
        params_validator.validate(action_obj.spec.params_schema, params)
        md = self.adapter.get_model_descriptor(admin.model)
        dummy_request = SimpleNamespace()
        qs = self.scope_query_service.build_queryset(
            admin, md, dummy_request, user, scope
        )
        result = await admin.perform_action(action, qs, params, user)
        if is_dataclass(result):
            return asdict(result)
        if isinstance(result, dict):
            return dict(result)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if hasattr(result, "dict") and callable(result.dict):
            return result.dict()
        if result is None:
            return {}
        if hasattr(result, "__dict__"):
            return dict(result.__dict__)
        return {"result": result}


admin_action_runner = AdminActionRunner()


__all__ = ["AdminActionRunner", "admin_action_runner"]

# The End

