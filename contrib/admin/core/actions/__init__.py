# -*- coding: utf-8 -*-
"""
actions

Action specification and base class for admin actions.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..permissions import PermAction


@dataclass
class ActionSpec:
    """Specification for an administrative action."""

    name: str
    label: str
    description: str
    danger: bool
    scope: list[str]
    params_schema: Dict[str, Any]
    required_perm: PermAction | None


@dataclass
class ActionResult:
    """Result of running an administrative action."""

    ok: bool
    affected: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    report: Optional[str] = None
    undo_token: Optional[str] = None


class BaseAction(ABC):
    """Base class for admin actions."""

    spec: ActionSpec

    def __init__(self, batch_size: int = 100) -> None:
        self.batch_size = batch_size
        self.admin: Any | None = None

    def bind_admin(self, admin: Any) -> "BaseAction":
        self.admin = admin
        return self

    def _user_has_perm(self, user: Any, codename: PermAction | None) -> bool:
        if self.admin is not None and hasattr(self.admin, "_user_has_perm"):
            return self.admin._user_has_perm(user, codename)
        if codename is None:
            return True
        if getattr(user, "is_superuser", False):
            return True
        perms = getattr(user, "permissions", None)
        if perms is None:
            return False
        return codename in perms

    @abstractmethod
    async def run(self, qs: Any, params: Dict[str, Any], user: Any) -> ActionResult:
        """Run the action on the given queryset."""


from .delete_selected import DeleteSelectedAction
from .tokens import ScopeTokenService
from .scope_query import ScopeQueryService


__all__ = [
    "ActionSpec",
    "ActionResult",
    "BaseAction",
    "DeleteSelectedAction",
    "ScopeTokenService",
    "ScopeQueryService",
]

# The End

