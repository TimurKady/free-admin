# -*- coding: utf-8 -*-
"""
Placeholder implementation for a file upload widget.

Version: 1.0.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from . import BaseWidget, register_widget


@register_widget("file-upload")
class FileUploadWidget(BaseWidget):
    """Placeholder widget for file uploads.

    Real initialisation (json-editor + BS5 + endpoints) will be added at the
    forms step.
    """

    pass


# The End
