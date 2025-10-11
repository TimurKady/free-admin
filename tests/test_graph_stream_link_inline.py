# -*- coding: utf-8 -*-
"""GraphStreamLink inline behavior tests.

Verify that inline list view filters links by their graph.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Callable, cast

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from tortoise import Tortoise

from freeadmin.core.site import AdminSite
from freeadmin.core.auth import admin_auth_service
from freeadmin.core.permissions import permission_checker
from freeadmin.router import AdminRouter
from freeadmin.boot import admin as boot_admin
from freeadmin.core.settings import system_config

from apps.streams.models import StreamGraph, GraphStreamLink, Stream
from apps.streams.admin.stream_graph import StreamGraphAdmin
from apps.streams.admin.links import GraphStreamLinkAdmin

from tests import adapter_models


class TestGraphStreamLinkInline:
    site: AdminSite
    perms_stub: "TestGraphStreamLinkInline.PermsStub"
    _orig_perm: Any
    user: SimpleNamespace
    app: FastAPI
    client: TestClient
    class PermissionStub:
        async def __call__(self, request: Request) -> None:  # pragma: no cover - stub
            return None

    class PermsStub:
        def __init__(self) -> None:
            self.deps: dict[Any, TestGraphStreamLinkInline.PermissionStub] = {}

        def require_model(
            self, *args: Any, **kwargs: Any
        ) -> "TestGraphStreamLinkInline.PermissionStub":
            dep = TestGraphStreamLinkInline.PermissionStub()
            key = args[0] if args else None
            self.deps[key] = dep
            return dep

    PermissionStub.__call__.__annotations__["request"] = Request

    @classmethod
    def setup_class(cls) -> None:
        asyncio.run(
            Tortoise.init(
                db_url="sqlite://:memory:",
                modules={
                    "models": [
                        "apps.streams.models.stream",
                        "apps.streams.models.connector",
                        "apps.streams.models.stream_graph",
                        "apps.streams.models.connections",
                        "apps.streams.models.links",
                        "apps.streams.models.pipeline",
                    ],
                    "admin": list(
                        {
                            adapter_models.models.user.__module__,
                            adapter_models.models.user_permission.__module__,
                            adapter_models.models.group.__module__,
                            adapter_models.models.group_permission.__module__,
                            adapter_models.models.content_type.__module__,
                            adapter_models.models.system_setting.__module__,
                        }
                    ),
                },
            )
        )
        asyncio.run(Tortoise.generate_schemas())
        asyncio.run(system_config.ensure_seed())
        cls.site = AdminSite(boot_admin.adapter, title="Test")
        cls.site.register("streams", StreamGraph, StreamGraphAdmin)
        cls.site.register("streams", GraphStreamLink, GraphStreamLinkAdmin)
        asyncio.run(cls.site.finalize())
        cls.perms_stub = cls.PermsStub()
        cls._orig_perm = permission_checker.require_model
        cast(Any, permission_checker).require_model = cls.perms_stub.require_model
        cls.user = SimpleNamespace(is_superuser=True)

        async def _current_user(request: Request) -> SimpleNamespace:
            return cls.user

        _current_user.__annotations__["request"] = Request

        cls.app = FastAPI()
        AdminRouter(cls.site).mount(cls.app)
        cls.app.dependency_overrides[admin_auth_service.get_current_admin_user] = _current_user
        cls.client = TestClient(cls.app)

    @classmethod
    def teardown_class(cls) -> None:
        cast(Any, permission_checker).require_model = cls._orig_perm
        asyncio.run(Tortoise.close_connections())

    def test_inline_filters_by_graph(self) -> None:
        graph = asyncio.run(StreamGraph.create(name="g1"))
        stream = asyncio.run(Stream.create(name="s1"))
        asyncio.run(GraphStreamLink.create(graph=graph, stream=stream))

        resp_spec = self.client.get(
            f"/panel/orm/streams/streamgraph/{graph.id}/_inlines"
        )
        assert resp_spec.status_code == 200
        spec = resp_spec.json()[0]
        assert spec["app"] == "streams"
        assert spec["parent_fk"] == "graph"
        assert spec["count"] == 1

        resp_links = self.client.get(
            f"/panel/orm/streams/graphstreamlink/_list?filter.graph.eq={graph.id}"
        )
        assert resp_links.status_code == 200
        data = resp_links.json()
        items = data["items"]
        assert len(items) == 1
        assert items[0]["graph_id"] == graph.name
        assert items[0]["stream_id"] == stream.name


# The End

