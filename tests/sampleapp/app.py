# -*- coding: utf-8 -*-
"""Test application configuration used in discovery tests."""

from __future__ import annotations

from freeadmin.core.interface.app import AppConfig


class SampleAppConfig(AppConfig):
    """Track lifecycle calls for verification in the test-suite."""

    app_label = "sampleapp"
    name = "tests.sampleapp"

    def __init__(self) -> None:
        """Initialize mutable counters for startup assertions."""

        super().__init__()
        self.ready_calls = 0

    async def startup(self) -> None:
        """Increment invocation counter to mark lifecycle activation."""

        self.ready_calls += 1


default = SampleAppConfig()

__all__ = ["SampleAppConfig", "default"]


# The End
