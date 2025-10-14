"""
__init__

Admin module entry point.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from .application import ApplicationFactory
from .conf import FreeAdminSettings, configure, current_settings
from .core.base import BaseModelAdmin
from .core.site import AdminSite
from .meta import __version__
from .router import AdminRouter

# The End

