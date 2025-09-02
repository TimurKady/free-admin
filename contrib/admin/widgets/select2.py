# -*- coding: utf-8 -*-
"""
select2

Remote select widget backed by Select2.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Dict

from ..boot import admin as boot_admin
from ..core.settings import SettingsKey, system_config
from .base import BaseWidget
from .registry import registry


@registry.register("select2")
class Select2Widget(BaseWidget):
    assets_css = (
        "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css",
    )
    assets_js = (
        "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js",
    )

    @property
    def base_url(self) -> str:
        prefix = system_config.get_cached(SettingsKey.API_PREFIX, "/api")
        lookup = system_config.get_cached(SettingsKey.API_LOOKUP, "/lookup")
        if lookup.startswith(prefix):
            return lookup
        return f"{prefix.rstrip('/')}/{lookup.lstrip('/')}"

    async def prefetch(self) -> None:  # pragma: no cover - network/database interactions
        fd = self.ctx.field
        rel = getattr(fd, "relation", None)
        inst = self.ctx.instance
        if not rel or inst is None:
            return

        try:
            RelModel = boot_admin.adapter.get_model(rel.target)
        except Exception:
            return

        pk_attr = boot_admin.adapter.get_pk_attr(RelModel)
        meta = dict(getattr(fd, "meta", {}) or {})

        if getattr(rel, "kind", "") == "m2m":
            await boot_admin.adapter.fetch_related(inst, self.ctx.name)
            related = getattr(inst, self.ctx.name) or []
            ids = [getattr(o, pk_attr) for o in sorted(related, key=lambda o: getattr(o, pk_attr))]
            setattr(inst, f"{self.ctx.name}_ids", ids)
            meta["choices_map"] = {str(getattr(o, pk_attr)): str(o) for o in related}
        else:
            cur = getattr(inst, f"{self.ctx.name}_id", None)
            if cur is not None:
                try:
                    obj = await boot_admin.adapter.get(RelModel, **{pk_attr: cur})
                    label = str(obj)
                except Exception:  # pragma: no cover - fallback
                    label = str(cur)
                meta["choices_map"] = {str(cur): label}
                meta["current_label"] = label

        object.__setattr__(fd, "meta", meta)

    def get_schema(self) -> Dict[str, Any]:
        fd = self.ctx.field
        rel = getattr(fd, "relation", None)
        title = self.get_title()
        is_many = bool(getattr(fd, "many", False) or (rel and getattr(rel, "kind", "") == "m2m"))

        md = self.ctx.descriptor
        ajax_url = f"{self.base_url}/{md.app_label}.{md.model_name}/{self.ctx.name}"
        ajax_opts = {"ajax": {"url": ajax_url, "delay": 250}}

        meta = getattr(fd, "meta", {}) or {}
        choices_map = meta.get("choices_map") or {}
        enum = list(choices_map.keys())
        titles = list(choices_map.values())

        if is_many:
            schema = {
                "type": "array",
                "title": title,
                "format": "select",
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": enum,
                    "options": {"enum_titles": titles},
                },
                "options": {"select2": ajax_opts},
            }
            return self.merge_readonly(schema)

        schema = {
            "type": "string",
            "title": title,
            "format": "select",
            "enum": enum,
            "options": {"enum_titles": titles, "select2": ajax_opts},
        }
        return self.merge_readonly(schema)

    def get_startval(self) -> Any:
        fd = self.ctx.field
        rel = getattr(fd, "relation", None)
        is_many = bool(getattr(fd, "many", False) or (rel and getattr(rel, "kind", "") == "m2m"))
        required = bool(getattr(fd, "required", False))

        if self.ctx.instance is None:
            if not required and not is_many:
                return ""
            return [] if is_many else None

        if rel:
            if is_many:
                ids = getattr(self.ctx.instance, f"{self.ctx.name}_ids", None)
                return [str(v) for v in ids] if ids is not None else []
            cur = getattr(self.ctx.instance, f"{self.ctx.name}_id", None)
            return "" if (cur is None and not required) else (str(cur) if cur is not None else None)

        return getattr(self.ctx.instance, self.ctx.name, None)

# The End

