# -*- coding: utf-8 -*-
"""crud

Compatibility facade exposing CRUD helpers.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from .contrib.crud.operations import (
    AsyncFileSaver as _AsyncFileSaver,
    CrudRouterBuilder as _CrudRouterBuilder,
    MAX_UPLOAD_SIZE as _MAX_UPLOAD_SIZE,
    SafePathSegment as _SafePathSegment,
)


class CrudCompatibilityFacade:
    """Provide accessors for CRUD helper symbols."""

    SafePathSegment = _SafePathSegment
    AsyncFileSaver = _AsyncFileSaver
    CrudRouterBuilder = _CrudRouterBuilder
    MAX_UPLOAD_SIZE = _MAX_UPLOAD_SIZE


SafePathSegment = CrudCompatibilityFacade.SafePathSegment
AsyncFileSaver = CrudCompatibilityFacade.AsyncFileSaver
CrudRouterBuilder = CrudCompatibilityFacade.CrudRouterBuilder
MAX_UPLOAD_SIZE = CrudCompatibilityFacade.MAX_UPLOAD_SIZE

__all__ = [
    "CrudCompatibilityFacade",
    "SafePathSegment",
    "AsyncFileSaver",
    "CrudRouterBuilder",
    "MAX_UPLOAD_SIZE",
]


# The End

