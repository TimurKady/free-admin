# -*- coding: utf-8 -*-
"""public pages

Test coverage for registering and exposing public FreeAdmin pages."""

from __future__ import annotations

from freeadmin.core.boot import admin as boot_admin
from freeadmin.core.interface.site import AdminSite
from freeadmin.core.network.router.aggregator import ExtendedRouterAggregator
from tests.conftest import admin_state


class TestPublicPageRegistration:
    """Validate registration and mounting of public pages."""

    site: AdminSite

    @classmethod
    def setup_class(cls) -> None:
        """Prepare a fresh admin site and register a public page."""

        admin_state.reset()
        cls.site = AdminSite(boot_admin.adapter, title="Public Page Test")

        @cls.site.register_public_view(
            path="/welcome",
            name="Welcome",
            template="pages/welcome.html",
        )
        async def welcome(request, user=None) -> dict[str, object]:
            """Provide additional context for the welcome page."""

            return {"subtitle": "Rendered from tests", "user": user}

    @classmethod
    def teardown_class(cls) -> None:
        """Restore the global admin state after tests complete."""

        admin_state.reset()

    def test_public_router_registration(self) -> None:
        """Ensure the page manager exposes routers for public pages."""

        routers = list(self.site.pages.iter_public_routers())
        assert len(routers) == 1
        router = routers[0]
        paths = sorted(getattr(route, "path", "") for route in router.routes)
        assert "/welcome" in paths

    def test_extended_aggregator_includes_public_routes(self) -> None:
        """Verify aggregated routers include registered public pages."""

        aggregator = ExtendedRouterAggregator(site=self.site)
        aggregator.add_admin_router(aggregator.get_admin_router())
        collected_routes: list[str] = []
        for router, prefix in aggregator.get_routers():
            if prefix not in (None, ""):
                continue
            for route in router.routes:
                path = getattr(route, "path", None)
                if path:
                    collected_routes.append(path)
        assert "/welcome" in collected_routes


# The End

