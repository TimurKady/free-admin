"""
__init__

Admin module entry point.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from .core.application import ApplicationFactory
from .core.configuration.conf import FreeAdminSettings, configure, current_settings
from .core.interface.base import BaseModelAdmin
from .core.interface.site import AdminSite
from .core.network.router import AdminRouter
from .meta import __version__

# The End

