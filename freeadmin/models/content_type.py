# -*- coding: utf-8 -*-
"""
content_type

Persistent Content Types for addressing admin model permissions.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from ..boot import admin as boot_admin

AdminContentType = boot_admin.adapter.content_type_model

__all__ = ["AdminContentType"]

# The End

