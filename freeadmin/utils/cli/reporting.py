# -*- coding: utf-8 -*-
"""
reporting

Utilities for reporting filesystem creation outcomes.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path
from typing import List


class CreationReport:
    """Track created and skipped filesystem entities for CLI scaffolding."""

    def __init__(self, root: Path) -> None:
        """Initialize report for a specific root path."""
        self.root = root
        self._created: List[Path] = []
        self._skipped: List[Path] = []

    @property
    def created(self) -> List[Path]:
        """Return the list of created filesystem paths."""
        return list(self._created)

    @property
    def skipped(self) -> List[Path]:
        """Return the list of skipped filesystem paths."""
        return list(self._skipped)

    def add_created(self, path: Path) -> None:
        """Record a path that has been newly created."""
        self._created.append(path)

    def add_skipped(self, path: Path) -> None:
        """Record a path that already existed and was skipped."""
        self._skipped.append(path)

    def created_any(self) -> bool:
        """Return True when at least one entity was created."""
        return bool(self._created)

    def skipped_any(self) -> bool:
        """Return True when at least one entity was skipped."""
        return bool(self._skipped)


# The End

