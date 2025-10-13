# -*- coding: utf-8 -*-
"""Ensure BootManager registers custom application models with Tortoise."""

from __future__ import annotations

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


# The End
