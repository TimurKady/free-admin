# -*- coding: utf-8 -*-
"""Application configuration used for BootManager registration tests."""

from __future__ import annotations

from freeadmin.core.app import AppConfig


class SampleAppConfig(AppConfig):
    """Expose models from the sample test application."""

    app_label = "sample"
    name = "tests.sample_app"
    models = ("tests.sample_app.models",)


default = SampleAppConfig()

__all__ = ["SampleAppConfig", "default"]


# The End
