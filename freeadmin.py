"""
__init__

Admin module entry point.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from importlib import import_module, util
from pathlib import Path
from types import ModuleType
from typing import Final

import sys


class BootstrapModuleLoader:
    """Load the namespace bootstrap helper from the hyphenated directory."""

    def __init__(self, module_name: str, file_path: Path) -> None:
        """Record the bootstrap module metadata for lazy loading."""
        self._module_name = module_name
        self._file_path = file_path
        self._module: ModuleType | None = None

    def ensure_loaded(self) -> ModuleType:
        """Import the bootstrap module and cache the loaded instance."""
        if self._module is None:
            spec = util.spec_from_file_location(self._module_name, self._file_path)
            if spec is None or spec.loader is None:
                message = "Unable to load the bootstrap module from the hyphenated directory."
                raise RuntimeError(message)
            module = util.module_from_spec(spec)
            sys.modules[self._module_name] = module
            spec.loader.exec_module(module)
            self._module = module
        return self._module


class HyphenatedPackageProxy:
    """Expose the canonical package API through the hyphenated module tree."""

    def __init__(self, package_name: str, loader: BootstrapModuleLoader) -> None:
        """Store the canonical package metadata alongside the bootstrap loader."""
        self._package_name = package_name
        self._loader = loader
        self._is_initialized = False

    def initialize(self) -> None:
        """Ensure the namespace bootstrapper wires the module path correctly."""
        module = self._loader.ensure_loaded()
        bootstrapper = module.NamespaceBootstrapper(sys.modules[self._package_name], module.CANDIDATES)
        bootstrapper.initialize()
        self._is_initialized = True

    def import_attribute(self, relative_module: str, attribute: str) -> object:
        """Import an attribute from the hyphenated module tree."""
        if not self._is_initialized:
            self.initialize()
        module = import_module(relative_module, self._package_name)
        return getattr(module, attribute)


PACKAGE_NAME: Final[str] = __name__
PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
BOOTSTRAP_MODULE_NAME: Final[str] = "free_admin._bootstrap"
BOOTSTRAP_PATH: Final[Path] = PACKAGE_ROOT / "free-admin" / "_bootstrap.py"

_loader = BootstrapModuleLoader(BOOTSTRAP_MODULE_NAME, BOOTSTRAP_PATH)
_proxy = HyphenatedPackageProxy(PACKAGE_NAME, _loader)
_proxy.initialize()

BaseModelAdmin = _proxy.import_attribute(".core.base", "BaseModelAdmin")
AdminSite = _proxy.import_attribute(".core.site", "AdminSite")
__version__ = _proxy.import_attribute(".meta", "__version__")
AdminRouter = _proxy.import_attribute(".router", "AdminRouter")
FreeAdminSettings = _proxy.import_attribute(".conf", "FreeAdminSettings")
configure = _proxy.import_attribute(".conf", "configure")
current_settings = _proxy.import_attribute(".conf", "current_settings")


# The End

