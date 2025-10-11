# -*- coding: utf-8 -*-
"""
__init__

Adapters for extending the admin interface.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from .base import BaseAdapter
from .registry import AdapterRegistry, registry

__all__ = ["BaseAdapter", "AdapterRegistry", "registry"]

# The End

