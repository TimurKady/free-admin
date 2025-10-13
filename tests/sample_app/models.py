# -*- coding: utf-8 -*-
"""Tortoise ORM models for the sample test application."""

from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class SampleNote(Model):
    """Represent a simple note used to verify model registration."""

    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=100)


__all__ = ["SampleNote"]


# The End
