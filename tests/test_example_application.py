# -*- coding: utf-8 -*-
"""
test_example_application

Smoke tests that validate the example application setup.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from example.config.main import ExampleApplication


class TestExampleApplicationSmoke:
    """Verify that the example application mounts the admin router."""

    def test_admin_router_mounted(self) -> None:
        """Ensure configuring the example attaches the admin site to the app."""

        application = ExampleApplication()
        app = application.configure()

        assert getattr(app.state, "admin_site", None) is not None


# The End

