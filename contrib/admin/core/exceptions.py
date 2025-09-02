# -*- coding: utf-8 -*-
"""
exceptions

Custom domain exceptions for the admin core.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations


class AdminError(Exception):
    """Base class for admin-specific exceptions."""


class ActionNotFound(AdminError):
    """Raised when an action is not registered."""


class PermissionDenied(AdminError):
    """Raised when a user lacks permission for an operation."""


class AdminModelNotFound(AdminError):
    """Raised when an admin model is not registered."""


class AdminIntegrityError(AdminError):
    """Raised when a data integrity issue occurs."""


# --- HTTP-like domain errors -------------------------------------------------

class HTTPError(AdminError):
    """Base class for exceptions carrying an HTTP status code."""

    status_code: int = 500

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or "")
        self.detail = detail


class BadRequestError(HTTPError):
    """Raised when a request fails validation or is malformed."""

    status_code = 400


class PermissionError(HTTPError):
    """Raised when an operation is not permitted."""

    status_code = 403


class NotFoundError(HTTPError):
    """Raised when a requested resource is not found."""

    status_code = 404


# The End

