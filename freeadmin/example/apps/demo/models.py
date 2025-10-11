# -*- coding: utf-8 -*-
"""
models

Tortoise ORM models that back the FreeAdmin demo application.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class DemoNote(Model):
    """Represent a short note managed through the demo administration UI."""

    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=120)
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "demo_notes"

    def __str__(self) -> str:
        """Return a concise textual representation of the note."""

        if self.created_at:
            return f"{self.title} ({self.created_at:%Y-%m-%d})"
        return self.title


__all__ = ["DemoNote"]


# The End
