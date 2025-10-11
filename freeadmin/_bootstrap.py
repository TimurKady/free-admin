"""
Namespace bootstrap utilities for the canonical freeadmin package.

This module ensures that imports continue to resolve even though the
physical package directory has been renamed to ``free-admin``.
"""

from __future__ import annotations

from importlib import invalidate_caches
from pathlib import Path
from types import ModuleType
from typing import Final, Iterable

import sys


class NamespaceBootstrapper:
    """Expose modules stored in the hyphenated directory through the canonical package."""

    def __init__(self, package: ModuleType, source_candidates: Iterable[Path]) -> None:
        """Store the package module alongside potential physical directory locations."""
        self._package = package
        self._source_candidates = tuple(source_candidates)
        self._source_dir: Path | None = None

    def initialize(self) -> None:
        """Populate import metadata so submodules resolve from the renamed directory."""
        source_dir = self._resolve_source_directory()
        path_entry = str(source_dir)
        package_path = list(getattr(self._package, "__path__", []))
        if path_entry not in package_path:
            package_path.append(path_entry)
        self._package.__path__ = package_path
        spec = getattr(self._package, "__spec__", None)
        if spec is not None:
            spec.submodule_search_locations = package_path
        init_file = source_dir / "__init__.py"
        if init_file.exists():
            self._package.__file__ = str(init_file)
        invalidate_caches()

    def _resolve_source_directory(self) -> Path:
        if self._source_dir is None:
            for candidate in self._source_candidates:
                if candidate.is_dir():
                    self._source_dir = candidate
                    break
            else:
                message = (
                    "Unable to locate the renamed 'free-admin' package directory."
                )
                raise RuntimeError(message)
        return self._source_dir


PACKAGE_NAME: Final[str] = __name__.rpartition(".")[0]
PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
CANDIDATES: Final[tuple[Path, ...]] = (
    PACKAGE_ROOT / "free-admin",
    PACKAGE_ROOT.parent / "free-admin",
)

bootstrapper = NamespaceBootstrapper(sys.modules[PACKAGE_NAME], CANDIDATES)
bootstrapper.initialize()


# The End

