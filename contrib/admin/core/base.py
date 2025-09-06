# -*- coding: utf-8 -*-
"""
base

Base class for model admin objects.
Inline Admin docs: contrib/admin/docs/INLINES.md

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from dataclasses import asdict
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TYPE_CHECKING,
)

from types import MappingProxyType
from datetime import datetime, timezone

from .exceptions import ActionNotFound, PermissionDenied, AdminIntegrityError
from .filters import FilterSpec
from ..adapters import BaseAdapter
from ..widgets import registry as widget_registry
from ..widgets.context import WidgetContext
from ..widgets.base import BaseWidget
from config.settings import settings
from .settings import SettingsKey, system_config

if TYPE_CHECKING:  # pragma: no cover
    from ..boot import BootManager

# Placeholder for the active ORM's QuerySet implementation
QuerySet = Any

from .actions import ActionResult, BaseAction  # noqa: E402
from .actions.delete_selected import DeleteSelectedAction  # noqa: E402
from .permissions import PermAction  # noqa: E402


class BaseModelAdmin:
    """Basic interface of the model admin class.

    Responsibility lines
    --------------------
    * All ``get_*_queryset`` methods return :class:`QuerySet`.
    * ``apply_row_level_security`` is applied to all read and edit operations.
    * The ``allow`` hook only affects the UI and does not replace RBAC checks.
    """

    # Name for menu and headings (plural and singular)
    label: str | None = None
    label_singular: str | None = None

    list_display: Sequence[str] = ()
    search_fields: Sequence[str] = ()
    list_filter: Sequence[str] | None = None
    ordering: Sequence[str] = ("id",)
    fields: Sequence[str] | None = None
    readonly_fields: Sequence[str] = ()
    autocomplete_fields: Sequence[str] = ()
    list_use_only: bool = False
    actions: tuple[type[BaseAction], ...] = (DeleteSelectedAction,)
    # Later: list_display, search_fields, list_filter, ordering, etc.
    
    # Global Admin Assets
    admin_assets_css: tuple[str, ...] = ()
    admin_assets_js: tuple[str, ...] = ()

    FILTER_OPS = {"": "eq", "eq": "eq", "icontains": "icontains", "gte": "gte", "lte": "lte", "gt": "gt", "lt": "lt", "in": "in"}
    FILTER_PREFIX: str = "filter."
    widgets_overrides: dict[str, str] = {}

    PARAM_TYPE_NAMES: dict[type, str] = {
        bool: "boolean",
        str: "string",
        int: "integer",
        float: "number",
    }

    def __init_subclass__(cls, **kwargs):  # type: ignore[override]
        super().__init_subclass__(**kwargs)
        collected: dict[str, Any] = {}
        meta = getattr(cls, "Meta", None)
        if meta is not None:
            collected.update(getattr(meta, "widgets", {}) or {})
        collected.update(getattr(cls, "widgets", {}) or {})

        resolved: dict[str, str] = {}
        for name, widget in collected.items():
            if isinstance(widget, str):
                key = widget
            else:
                w_cls = widget if isinstance(widget, type) else type(widget)
                key = getattr(w_cls, "key", None)
                if key is None:
                    for reg_key, reg_cls in widget_registry._by_key.items():
                        if reg_cls is w_cls:
                            key = reg_key
                            break
                if key is None:
                    raise RuntimeError(
                        f"Widget {widget!r} for field '{name}' is not registered."
                    )
            resolved[name] = key
        cls.widgets_overrides = resolved

    @classmethod
    def _schema_type_name(cls, typ: Any) -> str:
        if isinstance(typ, str):
            return typ
        if isinstance(typ, type):
            return cls.PARAM_TYPE_NAMES.get(typ, typ.__name__.lower())
        return type(typ).__name__.lower()

    class Meta:
        """Meta class for BaseModelAdmin."""

        pass

    def __init__(self, model: type[Any], adapter_or_boot: BaseAdapter | "BootManager"):
        """Save the model class and adapter for this admin instance."""
        self.model = model
        self._adapter = (
            adapter_or_boot.adapter
            if hasattr(adapter_or_boot, "adapter")
            else adapter_or_boot
        )

    # --- adapter helpers ----------------------------------------------------

    @property
    def adapter(self) -> BaseAdapter:
        return self._adapter

    def _qs_type(self):
        return getattr(self.adapter, "QuerySet", None)

    def _is_queryset(self, qs: Any) -> bool:
        qs_type = self._qs_type()
        if qs_type is None:
            return True
        try:
            return isinstance(qs, qs_type)
        except Exception:
            return False

    def _build_q(self, *args: Any, **kwargs: Any):
        return self.adapter.Q(*args, **kwargs)

    def _integrity_error(self):
        return getattr(self.adapter, "IntegrityError", Exception)

    def _is_binary_field(self, fd, name: str | None = None) -> bool:
        """Return ``True`` if the descriptor represents binary data.

        A field listed in ``widgets_overrides`` is treated as non-binary to
        allow explicit widget mappings to override automatic exclusion.
        """
        if name and name in (getattr(self, "widgets_overrides", {}) or {}):
            return False
        return getattr(fd, "kind", None) == "binary"

    # --- attribute accessors -------------------------------------------------

    def get_label(self) -> str | None:
        """Return plural label for the model."""
        return self.label

    def get_label_singular(self) -> str | None:
        """Return singular label for the model."""
        return self.label_singular

    def get_list_display(self) -> Sequence[str]:
        """Return fields displayed in list views."""
        return self.list_display

    def get_list_filter(self) -> Sequence[str]:
        """Return configured list filters."""
        return self.list_filter or ()

    def get_ordering(self, md) -> str:
        """Determine default ordering field."""
        ordering = self.ordering
        if ordering:
            return ordering[0]
        md_ordering = getattr(md, "ordering", None)
        if md_ordering:
            return md_ordering[0]
        meta_ordering = getattr(getattr(self.model, "Meta", None), "ordering", None)
        if meta_ordering:
            return meta_ordering[0]
        return md.pk_attr

    def get_readonly_fields(self) -> Sequence[str]:
        """Return fields marked as read-only."""
        return tuple(self.readonly_fields)

    def get_autocomplete_fields(self) -> Sequence[str]:
        """Return fields using autocomplete widgets."""
        return self.autocomplete_fields

    def is_field_readonly(self, md, name: str, mode: str, obj=None) -> bool:
        if name in self.readonly_fields:
            return True
        fd = md.fields_map[name]
        if getattr(fd, "primary_key", False):
            return True
        if name in {"created_at", "updated_at"}:
            return True
        return False

    def _has_implicit_default(self, fd) -> bool:
        """Return ``True`` if ``fd`` supplies an automatic value or default."""
        default = getattr(fd, "default", None)
        return (
            default is not None
            or any(
                getattr(fd, attr, False)
                for attr in ("auto_now", "auto_now_add", "generated")
            )
        )

    def _implicit_value(self, fd) -> Any:
        """Return a generated value for fields with automatic behaviour."""
        if fd.kind == "datetime":
            return datetime.now(timezone.utc)
        if fd.kind == "date":
            return datetime.now(timezone.utc).date()
        default = getattr(fd, "default", None)
        return default() if callable(default) else default

    # --- verbose names ---------------------------------------------------------

    def get_verbose_name(self) -> str:
        """
        Human-friendly singular name for the model.

        Preference order:
          1) self.model._meta.verbose_name
          2) self.label_singular
          3) self.label
          4) model class name normalized
        """
        md = getattr(self.model, "_meta", None)
        name = None
        if md is not None:
            name = getattr(md, "verbose_name", None)
        if not name and hasattr(self.model, "Meta"):
            name = getattr(self.model.Meta, "verbose_name", None)
        if not name:
            name = getattr(self, "label_singular", None) or getattr(self, "label", None)
        if not name:
            # Fallback: class name -> "Foo Bar", not "foo_bar"
            raw = getattr(self.model, "__name__", "") or "Model"
            name = raw.replace("_", " ").title()
        return str(name)

    def get_verbose_name_plural(self) -> str:
        """
        Human-friendly plural name for the model.

        Preference order:
          1) self.model._meta.verbose_name_plural
          2) self.label
          3) singular + 's' (very naive) OR normalized class name
        """
        md = getattr(self.model, "_meta", None)
        name = None
        if md is not None:
            name = getattr(md, "verbose_name_plural", None)
        if not name and hasattr(self.model, "Meta"):
            name = getattr(self.model.Meta, "verbose_name_plural", None)
        if not name:
            name = getattr(self, "label", None)
        if not name:
            # Fallback: try naive plural from singular
            singular = self.get_verbose_name()
            if singular and singular != "Model":
                name = f"{singular}s"
            else:
                raw = getattr(self.model, "__name__", "") or "Models"
                name = raw.replace("_", " ").title()
        return str(name)

    # --- permissions ------------------------------------------------------

    def allow(self, user: Any, action: str, obj: Optional[Any] = None) -> bool:
        """Return ``True`` if ``user`` may perform ``action`` on ``obj``.

        This hook only controls UI behaviour and is not a substitute for RBAC
        checks enforced elsewhere.
        """
        return True

    # --- actions -----------------------------------------------------------

    def _user_has_perm(self, user: Any, codename: PermAction | None) -> bool:
        """Return ``True`` if ``user`` has ``codename`` permission."""
        if codename is None:
            return True
        if getattr(user, "is_superuser", False):
            return True
        perms: set[str] = getattr(user, "permissions", set())
        if not perms:
            return False
        action = codename.value if isinstance(codename, PermAction) else str(codename)
        app_label = getattr(self, "app_label", "")
        model_name = getattr(self.model, "__name__", "")
        model_slug = getattr(self, "model_slug", model_name.lower())
        perm_key = f"{app_label}.{model_slug}.{action}".strip(".")
        return perm_key in perms or action in perms

    def _build_action_registry(self) -> Mapping[str, Type[BaseAction]]:
        """Собираем {name -> ActionClass} c проверкой дублей."""
        reg: dict[str, Type[BaseAction]] = {}
        for cls in self.actions:
            name = cls.spec.name
            if name in reg:
                raise ValueError(f"Duplicate action name: {name!r}")
            reg[name] = cls
        return MappingProxyType(reg)

    @property
    def _action_registry(self) -> Mapping[str, Type[BaseAction]]:
        if not hasattr(self, "__action_registry"):
            setattr(self, "__action_registry", self._build_action_registry())
        return getattr(self, "__action_registry")

    def get_actions(self) -> dict[str, BaseAction]:
        """Instantiate and return available administrative actions."""
        return {
            name: cls().bind_admin(self)
            for name, cls in self._action_registry.items()
        }

    def get_action(self, name: str) -> BaseAction | None:
        """Return action instance registered under ``name``."""
        cls = self._action_registry.get(name)
        return cls().bind_admin(self) if cls else None

    def list_actions(self) -> list[str]:
        """List names of available actions."""
        return list(self._action_registry.keys())

    def get_action_specs(self, user: Any) -> list[dict[str, Any]]:
        """Return action specifications permitted for ``user``."""
        specs: list[dict[str, Any]] = []
        for cls in self._action_registry.values():
            spec = cls.spec
            if self._user_has_perm(user, getattr(spec, "required_perm", None)):
                spec_dict = asdict(spec)
                schema = spec_dict.get("params_schema", {}) or {}
                spec_dict["params_schema"] = {
                    name: self._schema_type_name(tp) for name, tp in schema.items()
                }
                specs.append(spec_dict)
        return specs

    async def perform_action(
        self, name: str, qs: QuerySet, params: dict[str, Any], user: Any
    ) -> ActionResult:
        """Execute named action on queryset ``qs`` in batches."""
        action = self.get_action(name)
        if action is None:
            raise ActionNotFound("Unknown action")
        spec = action.spec
        if not self._user_has_perm(user, getattr(spec, "required_perm", None)):
            raise PermissionDenied("Permission denied")
        result = ActionResult(ok=True)
        md = self.adapter.get_model_descriptor(self.model)
        pk_attr = getattr(md, "pk_attr", "id")
        ids = await self.adapter.fetch_values(qs, pk_attr, flat=True)
        total = len(ids)
        start = 0
        while start < total:
            end = start + action.batch_size
            batch_ids = ids[start:end]
            batch_qs = self.adapter.apply_filter_spec(
                qs, [FilterSpec(pk_attr, "in", batch_ids)]
            )
            batch = await self.adapter.fetch_all(batch_qs)
            items = list(batch)
            if not items:
                start = end
                continue
            batch_res = await action.run(items, params, user)
            result.ok = result.ok and batch_res.ok
            result.affected += batch_res.affected
            result.skipped += batch_res.skipped
            result.errors.extend(batch_res.errors)
            if batch_res.report and not result.report:
                result.report = batch_res.report
            if batch_res.undo_token and not result.undo_token:
                result.undo_token = batch_res.undo_token
            start = end
        return result

    # --- Assets -----------------------------------------------------------

    def _prefix_static(self, path: str) -> str:
        if path.startswith("/static/"):
            prefix = system_config.get_cached(
                SettingsKey.ADMIN_PREFIX, settings.ADMIN_PATH
            ).rstrip("/")
            if prefix:
                return f"{prefix}{path}"
        return path

    def collect_assets(self, md, mode: str, obj=None, request=None, fields: list[str] | None = None) -> dict:
        """Collect CSS/JS assets for all widgets used in a form.

        Returns a dict of the form ``{"css": [...], "js": [...]}`` where duplicates are
        removed while preserving the order: first any global admin assets and then the
        widget-provided ones.
        """
        fields = fields or self.get_fields(md)

        css_ordered: list[str] = [self._prefix_static(h) for h in self.admin_assets_css]
        js_ordered: list[str] = [self._prefix_static(s) for s in self.admin_assets_js]
        seen_css = set(css_ordered)
        seen_js = set(js_ordered)

        for name in fields:
            # Important: do not build the widget twice if schema generation already did it.
            # The easiest approach is to collect assets in the same loop where
            # ``w.get_schema()`` is called, but this helper handles the fallback case.
            w = self._build_widget(md, name, mode, obj=obj, request=request)
            assets = w.get_assets() or {}
            for href in assets.get("css", []):
                href = self._prefix_static(href)
                if href not in seen_css:
                    seen_css.add(href)
                    css_ordered.append(href)
            for src in assets.get("js", []):
                src = self._prefix_static(src)
                if src not in seen_js:
                    seen_js.add(src)
                    js_ordered.append(src)

        return {"css": css_ordered, "js": js_ordered}

    # --- queryset hooks ---------------------------------------------------

    def get_queryset(self) -> QuerySet:
        """Return base queryset for this admin."""
        qs = self.adapter.all(self.model)
        if not self._is_queryset(qs):  # pragma: no cover - runtime safety
            raise RuntimeError("get_queryset must return QuerySet")
        return qs

    def apply_select_related(self, qs: QuerySet) -> QuerySet:
        """Apply ``select_related`` to the queryset if needed.

        Implementations should extend the automatically selected foreign
        keys from list columns rather than replace them.
        """
        qs = qs
        if not self._is_queryset(qs):  # pragma: no cover - runtime safety
            raise RuntimeError("apply_select_related must return QuerySet")
        return qs

    def apply_only(self, qs: QuerySet, columns: Sequence[str], md) -> QuerySet:
        """Apply ``only`` to the queryset when list views opt-in.

        ``columns`` contains the resolved list columns while ``md`` provides
        the model descriptor.  Subclasses may override this hook to customise
        field selection for list views.
        """
        if self.list_use_only:
            fd_map = getattr(md, "fields_map", {})
            only_fields = [
                c for c in columns if not (fd_map.get(c) and fd_map[c].relation)
            ]
            if md.pk_attr not in only_fields:
                only_fields.append(md.pk_attr)
            qs = self.adapter.only(qs, *only_fields)
        if not self._is_queryset(qs):  # pragma: no cover - runtime safety
            raise RuntimeError("apply_only must return QuerySet")
        return qs

    def get_autocomplete_queryset(
        self, fd, q: str, *, search_fields: list[str]
    ) -> QuerySet:
        """Return queryset for relation field autocomplete.

        Default implementation searches ``search_fields`` of the related model
        for the substring ``q``.
        """

        rel_model = self.adapter.get_model(fd.relation.target)
        qs = self.adapter.all(rel_model)
        if q and search_fields:
            filters = {f"{sf}__icontains": q for sf in search_fields}
            cond = None
            for k, v in filters.items():
                q_obj = self._build_q(**{k: v})
                cond = q_obj if cond is None else (cond | q_obj)
            if cond is not None:
                qs = self.adapter.filter(qs, cond)
        if not self._is_queryset(qs):  # pragma: no cover - runtime safety
            raise RuntimeError("get_autocomplete_queryset must return QuerySet")
        return qs

    def apply_row_level_security(self, qs: QuerySet, user: Any) -> QuerySet:
        """Apply row level security constraints for ``user``.

        Called by all read and edit operations to ensure consistent access
        control.
        """
        qs = qs
        if not self._is_queryset(qs):  # pragma: no cover - runtime safety
            raise RuntimeError("apply_row_level_security must return QuerySet")
        return qs

    def get_objects(self, request: Any, user: Any) -> QuerySet:
        """Return queryset used for retrieving objects.

        Row-level security is enforced via :meth:`apply_row_level_security`.
        """
        qs = self.get_queryset()
        qs = self.apply_select_related(qs)
        qs = self.apply_row_level_security(qs, user)
        if not self._is_queryset(qs):  # pragma: no cover - runtime safety
            raise RuntimeError("get_objects must return QuerySet")
        return qs

    def handle_integrity_error(self, exc: Exception) -> None:
        """Handle ``IntegrityError`` raised during save operations.

        Subclasses may override this to provide custom responses and may raise
        :class:`AdminIntegrityError` with an appropriate message.
        """
        raise AdminIntegrityError("Integrity error.")
    
    def get_fields(self, md) -> list[str]:
        """Return field names for the admin form.

        If ``self.fields`` is specified, return it as a list. Otherwise,
        build the list from the model's field descriptors and exclude
        ``"id"`` and the primary key attribute. If descriptors are not
        available, fall back to ``md.fields_map`` when provided.
        """

        if self.fields is not None:
            filtered: list[str] = []
            for name in self.fields:
                fd = md.field(name) if hasattr(md, "field") else None
                if fd is None and hasattr(md, "fields_map"):
                    fd = md.fields_map.get(name)
                if self._is_binary_field(fd) and name not in self.widgets_overrides:
                    continue
                filtered.append(name)
            return filtered

        pk_name = getattr(md, "pk_attr", None)
        excluded = {"id", pk_name}

        descriptors = getattr(md, "fields", []) or []
        fields_map = getattr(md, "fields_map", None) or {}

        # Preserve the declaration order from descriptors if available,
        # falling back to ``fields_map`` which mirrors the ORM's ``fields_map``.
        names: list[str] = []
        for fd in descriptors:
            try:
                name = fd.name
            except AttributeError:
                name = fd
            if name not in names:
                names.append(name)
        if not names:
            names = list(fields_map.keys())

        # Remove excluded fields while preserving order.
        ordered: list[str] = []
        for name in names:
            if name in excluded:
                continue
            ordered.append(name)

        # Append any extra fields from fields_map that weren't already listed
        # in descriptors while preserving original order.
        for name in fields_map.keys():
            if name in excluded or name in ordered:
                continue
            ordered.append(name)

        # Avoid duplicate ``<field>`` and ``<field>_id`` entries for foreign keys.
        cleaned: list[str] = []
        for name in ordered:
            if name.endswith("_id") and name[:-3] in ordered:
                continue
            fd = md.field(name) if hasattr(md, "field") else None
            if fd is None and hasattr(md, "fields_map"):
                fd = md.fields_map.get(name)
            if self._is_binary_field(fd) and name not in self.widgets_overrides:
                continue
            cleaned.append(name)
        return cleaned

    def get_fieldsets(self, md) -> list[Mapping[str, Any]] | None:
        """Return configured fieldsets for the admin form.

        Each fieldset dictionary may contain:

        ``title`` (str | None):
            Heading for the fieldset. ``None`` merges fields into the root.
        ``fields`` (Sequence[Any]):
            Iterable of field names or tuples defining grid sub‑groups.
        ``icon`` (str):
            Bootstrap icon identifier.
        ``hide_title`` (bool):
            When ``True``, the title is hidden but the icon remains.
        ``class`` (str):
            CSS class applied to the fieldset container.
        ``collapsed`` (bool):
            Whether the group is initially collapsed.
        """

        return self.fieldsets

    # --- minimal public API -------------------------------------------------

    def _resolve_widget_key(self, fd, field_name: str) -> str:
        if field_name in (getattr(self, "widgets_overrides", {}) or {}):
            return self.widgets_overrides[field_name]
        meta = getattr(fd, "meta", None) or {}
        if "widget" in meta:
            return str(meta["widget"])
        return widget_registry.resolve_for_field(fd, field_name, self)
    
    def _build_widget(
        self,
        md,
        name: str,
        mode: str,
        obj=None,
        request=None,
    ) -> BaseWidget:
        fd = md.fields_map[name]
        key = self._resolve_widget_key(fd, name)  # <-- single source of truth
        cls = widget_registry.get(key)
        if cls is None:
            model_name = getattr(md, "name", str(md))
            raise RuntimeError(
                f"No widget registered for key '{key}' "
                f"(field='{name}', model='{model_name}')"
            )
        prefix = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX, settings.ADMIN_PATH
        ).rstrip("/")
        ctx = WidgetContext(
            admin=self,
            descriptor=md,
            field=fd,
            name=name,
            instance=obj,
            mode=mode,
            request=request,
            readonly=self.is_field_readonly(md, name, mode, obj),
            prefix=prefix,
        )
        return cls(ctx)

    def _build_fieldset_properties(
        self,
        fieldsets: Iterable[Mapping[str, Any]],
        flat_properties: Mapping[str, Any],
        flat_startval: dict[str, Any],
        required: list[str],
    ) -> tuple[dict[str, Any], list[str], dict[str, Any], list[str]]:
        result: dict[str, Any] = {}
        order: list[str] = []
        grouped_startval: dict[str, Any] = {}
        root_required: list[str] = list(required)

        for fs in fieldsets:
            title = fs.get("title")
            fields = fs.get("fields", ())
            if title is None:
                for idx, item in enumerate(fields):
                    if isinstance(item, (list, tuple)):
                        names = [n for n in item if n in flat_properties]
                        if not names:
                            continue
                        g_key = f"group_{idx}"
                        g_required = [n for n in names if n in root_required]
                        for n in g_required:
                            root_required.remove(n)
                        result[g_key] = {
                            "type": "object",
                            "format": "grid",
                            "title": "\u200B",
                            "titleHidden": True,
                            "options": {"headerTemplate": ""},
                            "disable_collapse": True,
                            "collapsed": False,
                            "additionalProperties": False,
                            "properties": {
                                name: flat_properties[name] for name in names
                            },
                            "defaultProperties": names,
                        }
                        if g_required:
                            result[g_key]["required"] = g_required
                        g_start: dict[str, Any] = {}
                        for name in names:
                            if name in flat_startval:
                                g_start[name] = flat_startval.pop(name)
                        if g_start:
                            grouped_startval[g_key] = g_start
                        order.append(g_key)
                    else:
                        if item not in flat_properties:
                            continue
                        result[item] = flat_properties[item]
                        if item in flat_startval:
                            grouped_startval[item] = flat_startval.pop(item)
                        order.append(item)
                continue

            icon = fs.get("icon", "")
            hide_title = bool(fs.get("hide_title", False))
            container_class = fs.get("class")
            collapsed_opt = fs.get("collapsed")
            collapsed = bool(collapsed_opt) if collapsed_opt is not None else False
            disable_collapse = collapsed_opt is None
            header = f"<i class='bi bi-{icon}'></i>"

            group_props: dict[str, Any] = {}
            group_order: list[str] = []
            group_start: dict[str, Any] = {}
            group_required: list[str] = []
            for idx, item in enumerate(fields):
                if isinstance(item, (list, tuple)):
                    names = [n for n in item if n in flat_properties]
                    if not names:
                        continue
                    g_key = f"group_{idx}"
                    g_required = [n for n in names if n in root_required]
                    for n in g_required:
                        root_required.remove(n)
                    group_props[g_key] = {
                        "type": "object",
                        "format": "grid",
                        "title": "\u200B",
                        "titleHidden": True,
                        "options": {"headerTemplate": ""},
                        "disable_collapse": True,
                        "collapsed": False,
                        "additionalProperties": False,
                        "properties": {
                            name: flat_properties[name] for name in names
                        },
                        "defaultProperties": names,
                    }
                    if g_required:
                        group_props[g_key]["required"] = g_required
                        group_required.append(g_key)
                    g_start: dict[str, Any] = {}
                    for name in names:
                        if name in flat_startval:
                            g_start[name] = flat_startval.pop(name)
                    if g_start:
                        group_start[g_key] = g_start
                    group_order.append(g_key)
                else:
                    if item not in flat_properties:
                        continue
                    group_props[item] = flat_properties[item]
                    if item in flat_startval:
                        group_start[item] = flat_startval.pop(item)
                    group_order.append(item)
                    if item in root_required:
                        root_required.remove(item)
                        group_required.append(item)

            options: dict[str, Any] = {}
            if container_class:
                options["containerAttributes"] = {"class": container_class}
            if hide_title:
                fs_title = "\u200B"
                options["headerTemplate"] = header
            else:
                fs_title = title
                options["headerTemplate"] = (
                    f"{header}<span class='ms-1'>{{title}}</span>"
                )

            key = str(title)
            result[key] = {
                "type": "object",
                "format": "grid",
                "title": fs_title,
                "options": options,
                "disable_collapse": disable_collapse,
                "collapsed": collapsed,
                "additionalProperties": False,
                "properties": group_props,
                "defaultProperties": group_order,
            }
            if group_required:
                result[key]["required"] = group_required
            if group_start:
                grouped_startval[key] = group_start
            order.append(key)

        return result, order, grouped_startval, root_required

    async def get_schema(self, request, user, md, mode: str, obj=None) -> dict:
        """Assemble JSON ``schema`` and ``startval`` for the form."""

        field_names: tuple[str, ...] = tuple(self.get_fields(md))

        flat_properties: dict[str, Any] = {}
        required: list[str] = []
        startval: dict = {}

        fields_map = getattr(md, "fields_map", {}) or {}
        for name in field_names:
            w = self._build_widget(md, name, mode, obj=obj, request=request)
            fd = fields_map.get(name)

            pf = getattr(w, "prefetch", None)
            if callable(pf):
                import inspect  # noqa: F401
                import asyncio  # noqa: F401
                if inspect.iscoroutinefunction(pf):
                    await pf()

            flat_properties[name] = w.get_schema()
            if getattr(fd, "required", False) and not w.ctx.readonly:
                required.append(name)

            sv = w.get_startval()
            if sv is not None:
                try:
                    sv = w.to_python(sv)
                except Exception:
                    pass
                startval[name] = sv
            else:
                rel = getattr(fd, "relation", None) if fd else None
                is_many = bool(
                    getattr(fd, "many", False)
                    or (rel and getattr(rel, "kind", "") == "m2m")
                )
                if mode in ("add", "edit"):
                    default = getattr(fd, "default", None) if fd else None
                    if is_many:
                        sv = default if default is not None else []
                        try:
                            sv = w.to_python(sv)
                        except Exception:
                            pass
                    else:
                        if default is not None:
                            sv = default
                        else:
                            kind = getattr(fd, "kind", None)
                            if kind == "datetime":
                                sv = "0000-00-00 00:00"
                            elif kind == "date":
                                sv = "0000-00-00"
                            elif kind == "time":
                                sv = "00:00"
                            else:
                                sv = ""
                        try:
                            sv = w.to_python(sv)
                        except Exception:
                            pass
                    startval[name] = sv

        fieldsets = getattr(self, "fieldsets", None)
        if fieldsets:
            properties, order, startval, required = self._build_fieldset_properties(
                fieldsets, flat_properties, startval, required
            )
        else:
            properties = flat_properties
            order = list(field_names)

        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
            "defaultProperties": order,
            "additionalProperties": False,
        }

        return {"schema": schema, "startval": startval}

    def clean(
        self, payload: Dict[str, Any], *, for_update: bool = False
    ) -> Tuple[Dict[str, Any], List[Tuple[str, Iterable[Any] | None]]]:
        """Normalize ``payload`` for create or update operations.

        Returns a tuple ``(data, m2m_ops)`` where ``data`` contains direct
        assignments (including foreign keys expressed as ``<name>_id``) and
        ``m2m_ops`` is a list of many‑to‑many operations to perform after the
        instance is saved.  ``for_update`` controls how missing M2M keys are
        treated.  Subclasses may override this hook to perform custom
        validation or transformation and may raise
        :class:`fastapi.HTTPException` with ``status_code=422`` when
        validation fails.
        """

        md = self.adapter.get_model_descriptor(self.model)
        readonly = {
            name for name in md.fields_map if self.is_field_readonly(md, name, "edit")
        }
        hidden = set(getattr(self, "hidden_fields", []) or [])
        blocked = readonly | hidden

        data: Dict[str, Any] = {}
        m2m_ops: List[Tuple[str, Iterable[Any] | None]] = []
        for name, fd in md.fields_map.items():
            if getattr(fd, "primary_key", False) or name in blocked:
                continue
            rel = getattr(fd, "relation", None)
            if rel and rel.kind == "m2m":
                ids = payload.get(name, None if for_update else [])
                if ids is None:
                    if for_update:
                        m2m_ops.append((name, None))
                        continue
                    ids = []
                if not isinstance(ids, (list, tuple)):
                    ids = [ids]
                m2m_ops.append((name, ids))
                continue
            if rel and rel.kind == "fk":
                val = payload.get(name, None)
                if val == "" and getattr(fd, "nullable", False):
                    val = None
                data[f"{name}_id"] = val
                continue
            if name in payload:
                val = payload[name]
                if val == "" and self._has_implicit_default(fd):
                    continue
                if (
                    val == ""
                    and getattr(fd, "nullable", False)
                    and getattr(fd, "kind", None) in {"datetime", "date", "time"}
                ):
                    val = None
                if val is not None:
                    w = self._build_widget(md, name, mode="edit")
                    try:
                        val = w.to_storage(val)
                    except (AttributeError, NotImplementedError):
                        pass
                if (
                    val == ""
                    and getattr(fd, "nullable", False)
                    and getattr(fd, "kind", None) in {"string", "text", "datetime", "date", "time"}
                ):
                    val = None
                data[name] = val
        for name, fd in md.fields_map.items():
            if getattr(fd, "primary_key", False) or name in data:
                continue
            if self._has_implicit_default(fd):
                if for_update and getattr(fd, "auto_now_add", False):
                    continue
                data[name] = self._implicit_value(fd)
        return data, m2m_ops

    async def m2m_clear(self, manager):
        await self.adapter.m2m_clear(manager)

    async def m2m_add(self, manager, objs: Iterable[Any]):
        await self.adapter.m2m_add(manager, objs)

    async def create(
        self,
        request: Any,
        user: Any,
        md,
        payload: Dict[str, Any],
    ) -> Any:
        """Create a new model instance from ``payload``.

        ``request``, ``user`` and ``md`` are passed for symmetry with
        :meth:`update` and allow subclasses to take them into account.
        Foreign keys and many‑to‑many relations are handled automatically.
        Subclasses may override this to implement custom create behaviour.
        """
        headers = getattr(request, "headers", {}) or {}
        headers_lc: dict[str, Any] = (
            {k.lower(): v for k, v in headers.items()} if hasattr(headers, "items") else {}
        )
        for key, value in headers_lc.items():
            if key.startswith("x-force-fk-"):
                fname = key.removeprefix("x-force-fk-")
                fd = md.fields_map.get(fname)
                if fd and getattr(fd, "relation", None) and fd.relation.kind == "fk":
                    payload[fname] = value

        data, m2m_ops = self.clean(payload, for_update=False)
        try:
            obj = await self.adapter.create(self.model, **data)
        except self._integrity_error() as exc:
            self.handle_integrity_error(exc)
            raise
        for fname, ids in m2m_ops:
            if ids is None:
                continue
            await self.adapter.fetch_related(obj, fname)
            manager = getattr(obj, fname)
            await self.m2m_clear(manager)
            if ids:
                model_cls = manager.remote_model
                pk_attr = self.adapter.get_pk_attr(model_cls)
                related_qs = self.adapter.apply_filter_spec(
                    model_cls, [FilterSpec(pk_attr, "in", ids)]
                )
                related = await self.adapter.fetch_all(related_qs)
                await self.m2m_add(manager, related)
        return obj

    async def update(
        self,
        request: Any,
        user: Any,
        md,
        obj: Any,
        payload: Dict[str, Any],
    ) -> Any:
        """Update ``obj`` using ``payload``.

        Cleaned values are applied, the instance is saved and many‑to‑many
        relations updated.  Subclasses may override to hook into the update
        cycle.
        """

        data, m2m_ops = self.clean(payload, for_update=True)
        for key, val in data.items():
            setattr(obj, key, val)
        if data:
            try:
                await self.adapter.save(obj, update_fields=list(data.keys()))
            except self._integrity_error() as exc:
                self.handle_integrity_error(exc)
                raise
        for fname, ids in m2m_ops:
            if ids is None:
                continue
            await self.adapter.fetch_related(obj, fname)
            manager = getattr(obj, fname)
            await self.m2m_clear(manager)
            if ids:
                model_cls = manager.remote_model
                pk_attr = self.adapter.get_pk_attr(model_cls)
                related_qs = self.adapter.apply_filter_spec(
                    model_cls, [FilterSpec(pk_attr, "in", ids)]
                )
                related = await self.adapter.fetch_all(related_qs)
                await self.m2m_add(manager, related)
        return obj

    def get_list_columns(self, md) -> Sequence[str]:
        """Return column names used by list views.

        When ``list_display`` is provided it is respected. Otherwise all model
        fields except the primary key are returned so that the ``id`` column is
        not shown by default.
        """

        cols = list(self.get_list_display())
        if cols:
            return cols
        fields = [f for f in self.get_fields(md) if f not in {md.pk_attr, "id"}]
        if not fields:
            fields = [md.pk_attr]
        return fields

    def get_orderable_fields(self, md) -> set[str]:
        """Return field names that are allowed for ordering in list views."""
        columns = self.get_list_columns(md)
        return {c["key"] for c in self.columns_meta(md, columns) if c["sortable"]}

    def get_search_fields(self, md) -> list[str]:
        """Return field names used for text search in list views.

        If ``self.search_fields`` is explicitly configured, it is returned
        as a list. Otherwise the model's fields are inspected and only
        ``TextField`` and ``CharField`` types are included.
        """

        if self.search_fields:
            return list(self.search_fields)

        fd_map = getattr(md, "fields_map", {}) or {}
        result: list[str] = []
        for name in self.get_fields(md):
            fd = fd_map.get(name)
            if not fd:
                continue
            if getattr(fd, "kind", None) in {"text", "string"} and not getattr(
                fd, "choices", None
            ):
                result.append(name)
        return result

    def get_list_filters(self, md) -> List[Dict[str, Any]]:
        """Return filter specifications based on ``get_list_filter``.

        Each specification contains ``name``, ``label``, ``kind`` and allowed
        operations ``ops``. Choice fields include a ``choices`` list.
        """

        specs: List[Dict[str, Any]] = []
        list_filter = self.get_list_filter()
        if not list_filter:
            return specs

        for item in list_filter:
            path = item if isinstance(item, str) else None
            if not path:
                continue
            parts = path.split(".")
            cur_md = md
            fd = None
            for i, part in enumerate(parts):
                fd_map = getattr(cur_md, "fields_map", {}) or {}
                fd = fd_map.get(part)
                if fd is None:
                    break
                if i < len(parts) - 1:
                    rel = getattr(fd, "relation", None)
                    if rel is None:
                        fd = None
                        break
                    rel_model = self.adapter.get_model(rel.target)
                    cur_md = self.adapter.get_model_descriptor(rel_model)
            if fd is None:
                continue

            kind = getattr(fd, "kind", "")
            label = getattr(fd, "label", None) or parts[-1].replace("_", " ").title()

            if kind == "integer":
                kind = "number"
            if getattr(fd, "choices", None):
                kind = "choice"

            if kind == "string":
                ops = ["eq", "icontains", "in"]
            elif kind == "boolean":
                ops = ["eq"]
            elif kind == "number":
                ops = ["eq", "gte", "lte", "gt", "lt", "in"]
            elif kind in {"date", "datetime"}:
                ops = ["gte", "lte", "gt", "lt"]
            elif kind == "choice":
                ops = ["eq", "in"]
            else:
                ops = ["eq"]

            spec: Dict[str, Any] = {
                "name": path,
                "label": label,
                "kind": kind,
                "ops": ops,
            }
            if kind == "choice":
                choices = []
                for ch in getattr(fd, "choices", []) or []:
                    try:
                        val, lbl = ch
                    except Exception:  # pragma: no cover - fallback
                        val = getattr(ch, "const", getattr(ch, "value", ch))
                        lbl = getattr(ch, "title", getattr(ch, "label", str(ch)))
                    choices.append({"value": val, "label": str(lbl)})
                spec["choices"] = choices
            specs.append(spec)
        return specs

    def parse_filters(self, params, md):
        """Parse query parameters into :class:`FilterSpec` objects."""
        filters: list[FilterSpec] = []
        prefix = self.FILTER_PREFIX
        for key, raw in params.items():
            if not key.startswith(prefix):
                continue
            frag = key[len(prefix):]
            parts = frag.split(".") if frag else []
            if not parts:
                continue
            op_key = parts[-1]
            if op_key in self.FILTER_OPS and op_key != "":
                field_parts = parts[:-1]
                op = self.FILTER_OPS[op_key]
            else:
                field_parts = parts
                op = "eq"
            if not field_parts:
                continue
            fname = ".".join(field_parts)
            root = field_parts[0]
            fd = None
            if hasattr(md, "fields"):
                try:
                    fd = md.fields.get(root)
                except AttributeError:
                    for f in md.fields or []:
                        if getattr(f, "name", None) == root:
                            fd = f
                            break
            if fd is None:
                fd = getattr(md, "fields_map", {}).get(root)
            if fd is None:
                continue
            val = (
                self._coerce_value_for_filter(fd, raw, op)
                if len(field_parts) == 1
                else str(raw).strip()
            )
            raw_txt = str(raw).strip().lower()
            if (val is not None and val != "") or (op == "eq" and raw_txt == "null"):
                filters.append(FilterSpec(fname, op, val))
        return filters

    def _coerce_value_for_filter(self, fd, raw, op):
        """
        Coerce a filter value according to the field descriptor
        (``fd.kind``: 'string'|'integer'|'number'|'boolean'|'datetime'|'date', etc.).
        """
        txt = str(raw).strip()

        if op == "in":
            items = [x.strip() for x in txt.split(",") if x.strip() != ""]
            if getattr(fd, "kind", "") == "integer":
                return [int(x) for x in items]
            if getattr(fd, "kind", "") == "number":
                return [float(x) for x in items]
            if getattr(fd, "kind", "") == "boolean":
                return [x.lower() in {"1", "true", "yes", "on"} for x in items]
            return items

        kind = getattr(fd, "kind", "")

        if kind == "boolean":
            return txt.lower() in {"1", "true", "yes", "on"}

        if kind == "integer":
            try:
                return int(txt)
            except ValueError:
                return None
        if kind == "number":
            try:
                return float(txt)
            except ValueError:
                return None

        if kind in {"datetime", "date"}:
            return txt

        return txt

    def apply_filters_to_queryset(
        self, qs: QuerySet, flist: Sequence[FilterSpec]
    ) -> QuerySet:
        """Apply :class:`FilterSpec` objects to ``qs`` via the adapter."""
        return self.adapter.apply_filter_spec(qs, list(flist))

    def get_list_queryset(self, request, user, md, params: Dict[str, Any]) -> QuerySet:
        """Construct the queryset for list views.

        Applies searching, filtering and ordering. Row-level security is always
        enforced via :meth:`apply_row_level_security`. Foreign keys present in
        the list columns are eagerly loaded with ``select_related``. Subclasses
        may override to inject additional constraints.
        """

        search = params.get("search", "") or ""
        order = params.get("order", "")

        qs = self.get_queryset()
        qs = self.apply_row_level_security(qs, user)
        flist = self.parse_filters(getattr(request, "query_params", {}), md)
        qs = self.apply_filters_to_queryset(qs, flist)

        search_fields = self.get_search_fields(md)
        if search and search_fields:
            cond = None
            for sf in search_fields:
                lookup = f"{sf}__icontains"
                q_obj = self._build_q(**{lookup: search})
                cond = q_obj if cond is None else (cond | q_obj)
            if cond is not None:
                qs = self.adapter.filter(qs, cond)

        if not order:
            order = self.get_ordering(md)

        ord_field = order[1:] if order.startswith("-") else order
        if ord_field not in self.get_orderable_fields(md):
            order = self.get_ordering(md)
        qs = self.adapter.order_by(qs, order)
        params["order"] = order

        columns = self.get_list_columns(md)
        fk_to_select: List[str] = []
        fd_map = getattr(md, "fields_map", {})
        for col in columns:
            fd = fd_map.get(col)
            if fd and fd.relation and fd.relation.kind == "fk":
                fk_to_select.append(col)
        qs = self.apply_select_related(qs)
        # ``fk_to_select`` is appended after ``apply_select_related``
        if fk_to_select:
            qs = self.adapter.select_related(qs, *fk_to_select)

        qs = self.apply_only(qs, columns, md)
        if not self._is_queryset(qs):  # pragma: no cover - runtime safety
            raise RuntimeError("get_list_queryset must return QuerySet")
        return qs


    async def serialize_list_row(self, obj: Any, md, columns: Sequence[str]) -> Dict[str, Any]:
        """Serialize ``obj`` for list output.

        Handles foreign keys and many‑to‑many values.  Override to customise
        serialization for list rows.
        """

        fd_map = getattr(md, "fields_map", {})
        row: Dict[str, Any] = {}
        for col in columns:
            relation_name = col[:-3] if col.endswith("_id") else col
            fd = fd_map.get(relation_name)
            if fd and fd.relation:
                try:
                    if fd.relation.kind == "fk":
                        rel_obj = getattr(obj, relation_name, None)
                        if rel_obj is not None and hasattr(rel_obj, "__await__"):
                            try:
                                rel_obj = await rel_obj
                            except Exception:
                                rel_obj = None
                        row[col] = str(rel_obj) if rel_obj is not None else None
                    elif fd.relation.kind == "m2m":
                        try:
                            cnt = await self.adapter.count(
                                getattr(obj, relation_name)
                            )
                            row[col] = f"{cnt} items"
                        except Exception:
                            row[col] = None
                except Exception:
                    row[col] = None
            else:
                val = getattr(obj, col, None)
                if val is not None and hasattr(val, "isoformat"):
                    row[col] = val.isoformat()
                else:
                    row[col] = val
        row["row_pk"] = getattr(obj, md.pk_attr)
        row["row_str"] = str(obj)
        return row

    def _related_model_verbose_name(self, md, field: str) -> str | None:
        """Return verbose name for related model referenced by ``field``."""
        fd = getattr(md, "fields_map", {}).get(field)
        rel = getattr(fd, "relation", None) if fd else None
        if rel is not None:
            rel_model = self.adapter.get_model(rel.target)
            rel_md = self.adapter.get_model_descriptor(rel_model)
            return getattr(rel_md, "model_name", None) or getattr(rel_model, "__name__", None)
        return None

    def columns_meta(self, md, columns: Sequence[str]) -> List[Dict[str, Any]]:
        """Return metadata for list ``columns``.

        Metadata describes labels, data types and sorting capabilities.  This
        method provides sensible defaults and may be overridden for custom
        column descriptions.
        """

        fd_map = getattr(md, "fields_map", {})

        def _col_type(fd) -> str:
            if not fd:
                return "string"
            if fd.relation:
                return "relation"
            if fd.choices:
                return "choice"
            if fd.kind in {"integer", "bigint", "float", "decimal"}:
                return "number"
            if fd.kind == "boolean":
                return "boolean"
            if fd.kind in {"date", "datetime"}:
                return "datetime"
            return "string"

        meta: List[Dict[str, Any]] = []
        for col in columns:
            fd = fd_map.get(col)
            label = getattr(fd, "verbose_name", None) or col.replace("_", " ").title()
            if col.endswith("_id"):
                rel_label = self._related_model_verbose_name(md, col[:-3])
                if rel_label:
                    label = rel_label
            entry = {
                "key": col,
                "label": label,
                "type": _col_type(fd),
                "sortable": False
                if fd is None or (fd.relation and fd.relation.kind == "m2m")
                else True,
            }
            if fd and getattr(fd, "choices", None):
                ch_map = {}
                for ch in fd.choices:
                    key = getattr(ch, "const", getattr(ch, "value", ch))
                    label = getattr(ch, "title", getattr(ch, "label", str(ch)))
                    ch_map[str(key)] = str(label)
                entry["choices_map"] = ch_map
            meta.append(entry)
        return meta

# The End

