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

    _default_tokens: Tuple[Tuple[str, ...], ...] = (
        ("no such table",),
        ("missing table",),
        ("missing relation",),
        ("undefined table",),
        ("unknown table",),
        ("relation", "does not exist"),
        ("table", "does not exist"),
        ("column", "does not exist"),
        ("index", "does not exist"),
    )

    _missing_schema_error_names: Tuple[str, ...] = (
        "NoSuchTableError",
        "NoSuchColumnError",
        "UndefinedTable",
        "UndefinedColumn",
    )

    def __init__(
        self,
        *,
        tokens: Iterable[str] | Iterable[Iterable[str]] | None = None,
    ) -> None:
        """Store the lowercase token combinations used to match database errors."""

        selected = tokens if tokens is not None else self._default_tokens
        self._tokens: Tuple[Tuple[str, ...], ...] = self._normalize_tokens(selected)

    def is_missing_schema(self, error: BaseException | None) -> bool:
        """Return ``True`` when ``error`` signals absent migration artefacts."""

        if error is None:
            return False
        for candidate in self._iterate_error_chain(error):
            if self._matches_known_error_type(candidate):
                return True
            message = str(candidate).lower()
            if any(
                all(part in message for part in combination)
                for combination in self._tokens
            ):
                return True
        return False

    def _matches_known_error_type(self, error: BaseException) -> bool:
        """Return ``True`` when ``error`` has a class name associated with schema misses."""

        name = type(error).__name__
        return name in self._missing_schema_error_names

    def _normalize_tokens(
        self, selected: Iterable[str] | Iterable[Iterable[str]]
    ) -> Tuple[Tuple[str, ...], ...]:
        """Convert ``selected`` token definitions into normalized lowercase tuples."""

        normalized: list[Tuple[str, ...]] = []
        for combination in selected:
            if isinstance(combination, str):
                normalized.append((combination.lower(),))
            else:
                normalized.append(tuple(part.lower() for part in combination))
        return tuple(normalized)

    def _iterate_error_chain(self, error: BaseException) -> Iterator[BaseException]:
        """Yield every exception linked to ``error`` via ``__cause__``/``__context__``."""

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
