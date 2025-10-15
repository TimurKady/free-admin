# -*- coding: utf-8 -*-
"""
migration_errors

Helpers for classifying database exceptions that stem from missing migrations.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Iterable, Iterator, Tuple


class MigrationErrorClassifier:
    """Classify database errors that originate from missing schema objects."""

    _default_tokens: Tuple[str, ...] = (
        "no such table",
        "does not exist",
        "missing table",
        "missing relation",
        "undefined table",
        "unknown table",
    )

    def __init__(self, *, tokens: Iterable[str] | None = None) -> None:
        """Store the lowercase token set used to match database errors."""

        selected = tokens if tokens is not None else self._default_tokens
        self._tokens: Tuple[str, ...] = tuple(token.lower() for token in selected)

    def is_missing_schema(self, error: BaseException | None) -> bool:
        """Return ``True`` when ``error`` signals absent migration artefacts."""

        if error is None:
            return False
        for candidate in self._iterate_error_chain(error):
            message = str(candidate).lower()
            if any(token in message for token in self._tokens):
                return True
        return False

    def _iterate_error_chain(self, error: BaseException) -> Iterator[BaseException]:
        seen: set[int] = set()
        stack: list[BaseException] = [error]
        while stack:
            current = stack.pop()
            identifier = id(current)
            if identifier in seen:
                continue
            seen.add(identifier)
            yield current
            cause = getattr(current, "__cause__", None)
            if isinstance(cause, BaseException):
                stack.append(cause)
            context = getattr(current, "__context__", None)
            if isinstance(context, BaseException):
                stack.append(context)


# The End
