# -*- coding: utf-8 -*-
"""
Persistent Content Types for addressing admin model permissions.
"""

from tortoise import fields
from tortoise.models import Model


class AdminContentType(Model):
    id = fields.IntField(pk=True)
    app_label = fields.CharField(max_length=100, index=True)
    model = fields.CharField(max_length=150, index=True)
    dotted = fields.CharField(max_length=255, unique=True)  # "app.Model"
    is_registered = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "admin_content_type"
        unique_together = (("app_label", "model"),)

    def __str__(self) -> str:
        return self.dotted
