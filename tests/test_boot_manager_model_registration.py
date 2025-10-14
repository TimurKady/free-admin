# -*- coding: utf-8 -*-
"""Ensure BootManager registers custom application models with Tortoise."""

from __future__ import annotations

import logging
from typing import List, Tuple

from tortoise import Tortoise

from freeadmin.boot import BootManager


def test_boot_manager_registers_custom_models(monkeypatch) -> None:
    """Ensure BootManager registers models from AppConfig only once."""

    calls: List[Tuple[Tuple[str, ...], str]] = []
    original_init_models = Tortoise.init_models

    def _record(modules: List[str], app_label: str) -> None:
        calls.append((tuple(modules), app_label))
        original_init_models(modules, app_label)

    monkeypatch.setattr(Tortoise, "init_models", _record)

    boot = BootManager(adapter_name="tortoise")
    boot.load_app_config("tests.sample_app")
    _ = boot.adapter

    sample_calls = [entry for entry in calls if entry[1] == "sample"]
    assert sample_calls
    assert "sample" in Tortoise.apps
    assert "SampleNote" in Tortoise.apps["sample"]

    boot.load_app_config("tests.sample_app")
    sample_calls = [entry for entry in calls if entry[1] == "sample"]
    assert len(sample_calls) == 1

    boot.reset()
    Tortoise.apps.pop("sample", None)


def test_boot_manager_logs_missing_model_modules(monkeypatch, caplog) -> None:
    """Ensure missing model modules do not crash registration and emit a warning."""

    missing_module = "tests.sample_app.missing_models"

    from tests.sample_app.app import SampleAppConfig
    from freeadmin.boot import registry as model_registry

    def _missing_models(self) -> list[str]:
        return [missing_module]

    monkeypatch.setattr(SampleAppConfig, "get_models_modules", _missing_models, raising=False)

    original_import = model_registry.import_module

    def _guarded_import(name: str, package: str | None = None):
        if name == missing_module:
            raise ModuleNotFoundError(
                f"No module named '{missing_module}'",
                name=missing_module,
            )
        return original_import(name, package)

    monkeypatch.setattr(model_registry, "import_module", _guarded_import)

    boot = BootManager(adapter_name="tortoise")

    with caplog.at_level(logging.WARNING, logger=model_registry.LOGGER.name):
        boot.load_app_config("tests.sample_app")
        _ = boot.adapter

    warnings = [
        record
        for record in caplog.records
        if record.levelno == logging.WARNING
        and "no modules available" in record.getMessage()
    ]
    assert warnings

    boot.reset()


# The End
