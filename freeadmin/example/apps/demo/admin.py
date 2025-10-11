# -*- coding: utf-8 -*-
"""
admin

Administrative configuration for the FreeAdmin demo models.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from freeadmin.core.models import ModelAdmin
from freeadmin.hub import admin_site

from .models import DemoNote


class DemoNoteAdmin(ModelAdmin):
    """Expose :class:`DemoNote` records to the administration interface."""

    label = "Demo Notes"
    label_singular = "Demo Note"
    list_display = ("id", "title", "created_at")
    search_fields = ("title", "content")
    ordering = ("-created_at",)


admin_site.register(app="demo", model=DemoNote, admin_cls=DemoNoteAdmin, icon="bi-journal-text")


__all__ = ["DemoNoteAdmin"]


# The End
