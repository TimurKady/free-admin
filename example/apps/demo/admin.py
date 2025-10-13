"""
Place your admin classes for your ORM models here
"""

from __future__ import annotations

from freeadmin.core.models import ModelAdmin
from freeadmin.hub import admin_site

from .models import DemoNote


class DemoNoteAdmin(ModelAdmin):
    """Expose DemoNote instances through the administration interface."""

    model = DemoNote
    label = "Demo notes"
    list_display = ("id", "title", "created_at")
    search_fields = ("title", "body")


admin_site.register(app="demo", model=DemoNote, admin_cls=DemoNoteAdmin)


__all__ = ["DemoNoteAdmin"]

# The End
