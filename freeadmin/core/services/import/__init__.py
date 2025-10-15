# -*- coding: utf-8 -*-
"""
__init__

Compatibility bridge exposing import services from the interface layer.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from importlib import import_module

_import_module = import_module("freeadmin.core.interface.services.import")

ImportReport = _import_module.ImportReport
ImportService = _import_module.ImportService
parser_registry = _import_module.parser_registry

__all__ = ["ImportReport", "ImportService", "parser_registry"]


# The End

