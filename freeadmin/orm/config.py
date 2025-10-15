# -*- coding: utf-8 -*-
"""
config

Compatibility facade exposing ORM configuration helpers.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from importlib import import_module

_orm_module = import_module("freeadmin.core.data.orm.config")

ORMConfig = _orm_module.ORMConfig
ORMLifecycle = _orm_module.ORMLifecycle
Tortoise = _orm_module.Tortoise
tortoise_exceptions = _orm_module.tortoise_exceptions
MigrationErrorClassifier = _orm_module.MigrationErrorClassifier

__all__ = [
    "ORMConfig",
    "ORMLifecycle",
    "Tortoise",
    "tortoise_exceptions",
    "MigrationErrorClassifier",
]


# The End

