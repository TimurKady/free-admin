# -*- coding: utf-8 -*-
"""test_models_import

Smoke tests for ``freeadmin.models`` public exports.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from freeadmin import models


class TestModelsImport:
    """Smoke test suite validating ``freeadmin.models`` exports."""

    def test_adapter_models_are_reachable(self) -> None:
        """Ensure adapter-backed admin models are exposed on the package."""

        assert getattr(models, "AdminUser", None) is not None
        assert getattr(models, "AdminUserPermission", None) is not None
        assert getattr(models, "AdminGroup", None) is not None
        assert getattr(models, "AdminGroupPermission", None) is not None
        assert getattr(models, "AdminContentType", None) is not None
        assert getattr(models, "SystemSetting", None) is not None


# The End

