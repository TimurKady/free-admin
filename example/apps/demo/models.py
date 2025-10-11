"""
Place your ORM models here
"""

from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class DemoNote(Model):
    """Represent a short textual note stored for the demo panel."""

    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=120)
    body = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "demo_note"

    def __str__(self) -> str:
        """Return the note title for human-friendly identification."""

        return self.title


__all__ = ["DemoNote"]

# The End
