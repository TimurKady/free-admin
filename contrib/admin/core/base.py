# -*- coding: utf-8 -*-
"""
Base class for model admin objects.

Version: 1.0.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, cast

from fastapi import HTTPException
from tortoise import Tortoise, fields as tfields
from tortoise.exceptions import IntegrityError
from tortoise.expressions import Q
from tortoise.fields.relational import (
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
)
from tortoise.queryset import QuerySet


class BaseModelAdmin:
    """Basic interface of the model admin class.

    Линия ответственности
    ----------------------
    * Все ``get_*_queryset`` возвращают :class:`~tortoise.queryset.QuerySet`.
    * ``apply_row_level_security`` применяется для всех операций чтения и
      редактирования.
    * Хук ``allow`` влияет только на UI и не заменяет проверку прав (RBAC).
    """

    # Name for menu and headings (plural and singular)
    label: str | None = None
    label_singular: str | None = None

    list_display: Sequence[str] = ()
    search_fields: Sequence[str] = ()
    list_filter: Sequence[str] | None = None
    ordering: Sequence[str] = ("id",)
    fieldsets: tuple[tuple[str, dict[str, Any]], ...] | None = None
    fields: Sequence[str] | None = None
    readonly_fields: Sequence[str] = ()
    autocomplete_fields: Sequence[str] = ()
    list_use_only: bool = False
    # Later: list_display, search_fields, list_filter, ordering, fieldsets, etc.

    FILTER_OPS = {"": "eq", "icontains": "icontains", "gte": "gte", "lte": "lte", "gt": "gt", "lt": "lt", "in": "in"}

    class Meta:
        """Meta class for BaseModelAdmin."""

        pass

    def __init__(self, model: type[Any]):
        """Save the model class administered by this instance."""
        self.model = model

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

    # --- queryset hooks ---------------------------------------------------

    def get_base_queryset(self) -> QuerySet:
        """Return base queryset for this admin."""
        qs = self.model.all()
        if not isinstance(qs, QuerySet):  # pragma: no cover - runtime safety
            raise RuntimeError("get_base_queryset must return QuerySet")
        return qs

    def apply_select_related(self, qs: QuerySet) -> QuerySet:
        """Apply ``select_related`` to the queryset if needed.

        Implementations should extend the automatically selected foreign
        keys from list columns rather than replace them.
        """
        qs = qs
        if not isinstance(qs, QuerySet):  # pragma: no cover - runtime safety
            raise RuntimeError("apply_select_related must return QuerySet")
        return qs

    def apply_only(self, qs: QuerySet, columns: Sequence[str], md) -> QuerySet:
        """Apply ``only`` to the queryset when list views opt-in.

        ``columns`` contains the resolved list columns while ``md`` provides
        the model descriptor.  Subclasses may override this hook to customise
        field selection for list views.
        """
        if self.list_use_only:
            only_fields = list(columns)
            if md.pk_attr not in only_fields:
                only_fields.append(md.pk_attr)
            qs = qs.only(*only_fields)
        if not isinstance(qs, QuerySet):  # pragma: no cover - runtime safety
            raise RuntimeError("apply_only must return QuerySet")
        return qs

    def get_autocomplete_queryset(
        self, fd, q: str, *, search_fields: list[str]
    ) -> QuerySet:
        """Return queryset for relation field autocomplete.

        Default implementation searches ``search_fields`` of the related model
        for the substring ``q``.
        """

        if hasattr(Tortoise, "get_model"):
            rel_model = Tortoise.get_model(fd.relation.target)
        else:  # pragma: no cover - older Tortoise versions
            app_label, model_name = fd.relation.target.rsplit(".", 1)
            rel_model = Tortoise.apps.get(app_label, {}).get(model_name)
        qs = rel_model.all()
        if q and search_fields:
            filters = {f"{sf}__icontains": q for sf in search_fields}
            cond = None
            for k, v in filters.items():
                q_obj = Q(**{k: v})
                cond = q_obj if cond is None else (cond | q_obj)
            if cond is not None:
                qs = qs.filter(cond)
        if not isinstance(qs, QuerySet):  # pragma: no cover - runtime safety
            raise RuntimeError("get_autocomplete_queryset must return QuerySet")
        return qs

    def apply_row_level_security(self, qs: QuerySet, user: Any) -> QuerySet:
        """Apply row level security constraints for ``user``.

        Called by all read and edit operations to ensure consistent access
        control.
        """
        qs = qs
        if not isinstance(qs, QuerySet):  # pragma: no cover - runtime safety
            raise RuntimeError("apply_row_level_security must return QuerySet")
        return qs

    def get_object_queryset(self, request: Any, user: Any) -> QuerySet:
        """Return queryset used for retrieving a single object.

        Row-level security is enforced via :meth:`apply_row_level_security`.
        """
        qs = self.get_base_queryset()
        qs = self.apply_select_related(qs)
        qs = self.apply_row_level_security(qs, user)
        if not isinstance(qs, QuerySet):  # pragma: no cover - runtime safety
            raise RuntimeError("get_object_queryset must return QuerySet")
        return qs

    def handle_integrity_error(self, exc: IntegrityError) -> None:
        """Handle ``IntegrityError`` raised during save operations.

        Subclasses may override this to provide custom responses.
        """
        raise HTTPException(status_code=400, detail="Integrity error.")
    
    def get_fields(self, md) -> list[str]:
        """Return field names for the admin form.

        If ``self.fields`` is specified, return it as a list. Otherwise,
        build the list from the model's field descriptors and exclude
        ``"id"`` and the primary key attribute. If descriptors are not
        available, fall back to ``md.fields_map`` when provided.
        """

        if self.fields is not None:
            return list(self.fields)

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
            cleaned.append(name)
        return cleaned

    def get_fieldsets(self, md) -> tuple[tuple[str, dict[str, Any]], ...]:
        """Return configured fieldsets for the admin form."""

        if self.fieldsets is not None:
            return self.fieldsets

        return (("Main", {"fields": self.get_fields(md)}),)

    # --- minimal public API -------------------------------------------------

    def field_mapping(self, fd) -> dict:
        """Map a field descriptor to a JSON Schema fragment."""

        kind = cast(str | None, getattr(fd, "kind", None))
        rel = getattr(fd, "relation", None)
        if rel:
            if getattr(rel, "kind", None) == "m2m":
                return {"type": "array", "items": {"type": "string"}}
            if getattr(rel, "kind", None) == "fk":
                return {"type": "string"}
        mapping = {
            "text": {"type": "string", "format": "textarea"},
            "string": {"type": "string"},
            "boolean": {"type": "boolean"},
            "integer": {"type": "integer"},
            "bigint": {"type": "integer"},
            "float": {"type": "number"},
            "decimal": {"type": "number"},
            "date": {"type": "string", "format": "date"},
            "datetime": {"type": "string", "format": "date-time"},
            "uuid": {"type": "string", "format": "uuid"},
            "json": {"type": "object"},
        }
        return mapping.get(kind or "", {"type": "string"})

    async def get_schema(self, request, user, md, mode: str) -> Dict[str, Any]:
        """Build a basic JSON Schema and start values for the form."""

        properties: Dict[str, Any] = {}
        required: List[str] = []
        fields = self.get_fields(md)
        for order, name in enumerate(fields):
            fd = md.fields_map.get(name)
            if fd is None:
                for f in getattr(md, "fields", []) or []:
                    if getattr(f, "name", None) == name:
                        fd = f
                        break
            prop = self.field_mapping(fd)
            is_nullable = getattr(fd, "nullable", False) or getattr(fd, "null", False)
            kind = getattr(fd, "kind", "")
            if is_nullable and kind not in {"string", "text"}:
                t = prop.get("type")
                if isinstance(t, list):
                    if "null" not in t:
                        prop["type"] = t + ["null"]
                elif isinstance(t, str):
                    prop["type"] = [t, "null"]
            title = getattr(fd, "verbose_name", None) or name.replace("_", " ").title()
            prop["title"] = title
            prop["propertyOrder"] = order
            properties[name] = prop
            if (
                not (getattr(fd, "nullable", False) or getattr(fd, "null", False))
                and not (getattr(fd, "relation", None) and getattr(fd.relation, "kind", "") == "m2m")
                and getattr(fd, "default", None) is None
                and getattr(fd, "default_factory", None) is None
            ):
                required.append(name)

        schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "required": required,
            # Ensure JSON‑Editor sees all fields from ``get_fields``
            # and renders them in the same order.
            "defaultProperties": list(fields),
            "additionalProperties": False,
        }

        startval: Dict[str, Any] = {}
        if mode == "edit":
            pk = None
            if hasattr(request, "query_params"):
                pk = request.query_params.get("pk")
            if pk:
                # ``get_object_queryset`` enforces row level security.  Do not
                # bypass it when retrieving objects for form editing.
                qs = self.get_object_queryset(request, user)
                obj = await qs.get(**{md.pk_attr: pk})
                data: Dict[str, Any] = {}
                for name in fields:
                    fd = md.fields_map.get(name)
                    val = getattr(obj, name, None)
                    if fd and fd.relation and fd.relation.kind == "fk":
                        val = getattr(obj, f"{name}_id", None)
                    elif fd and getattr(fd, "relation", None) and fd.relation.kind == "m2m":
                        rel_pk = getattr(fd.relation, "to_field", "id")
                        rel_qs = await getattr(obj, name).all().values_list(rel_pk, flat=True)
                        val = list(rel_qs)
                    if fd and fd.kind == "text" and fd.nullable and val is None:
                        val = ""
                    data[name] = val
                startval = data
        else:
            for name in fields:
                fd = md.fields_map.get(name)
                if fd is None:
                    continue
                val: Any
                if getattr(fd, "relation", None) and fd.relation.kind == "m2m":
                    val = []
                elif getattr(fd, "default", None) is not None:
                    val = fd.default() if callable(fd.default) else fd.default
                elif getattr(fd, "default_factory", None):
                    try:
                        val = fd.default_factory()  # type: ignore[attr-defined]
                    except Exception:  # pragma: no cover - defensive
                        continue
                elif getattr(fd, "nullable", False) or getattr(fd, "null", False):
                    if getattr(fd, "kind", "") in {"string", "text"}:
                        val = ""
                    else:
                        val = None
                else:
                    continue
                startval[name] = val

        return {"schema": schema, "startval": startval}

    async def build_ui(self, request, user, md, mode: str) -> Dict[str, Any]:
        """Return a minimal uiSchema for JSON‑Editor."""

        ui: Dict[str, Any] = {}
        fields = self.get_fields(md)
        readonly = set(getattr(self, "readonly_fields", []) or [])
        hidden = set(getattr(self, "hidden_fields", []) or [])

        for name in fields:
            fd = md.fields_map.get(name)
            if fd and fd.kind == "text":
                ui[name] = {"ui:widget": "textarea", "ui:options": {"rows": 6}}
            if name in hidden:
                ui.setdefault(name, {})["ui:widget"] = "hidden"
            if name in readonly:
                ui.setdefault(name, {})["ui:readonly"] = True

        ui["ui:order"] = list(fields)
        return ui

    def clean(self, payload: dict) -> dict:
        """Validate ``payload`` before saving.

        Subclasses may override this method and raise
        :class:`fastapi.HTTPException` with ``status_code=422`` and
        ``detail`` containing ``{"errors": {...}, "detail": "..."}`` when
        server-side validation fails.  The base implementation simply
        returns ``payload`` unchanged.
        """

        return payload

    def clean_payload(
        self, payload: Dict[str, Any], *, for_update: bool = False
    ) -> Tuple[Dict[str, Any], List[Tuple[str, Iterable[Any] | None]]]:
        """Normalize ``payload`` for create or update operations.

        Returns a tuple ``(data, m2m_ops)`` where ``data`` contains direct
        assignments (including foreign keys expressed as ``<name>_id``) and
        ``m2m_ops`` is a list of many‑to‑many operations to perform after the
        instance is saved.  ``for_update`` controls how missing M2M keys are
        treated.  Subclasses can override this hook to perform custom
        validation or transformation.
        """

        md = self.model._meta
        readonly = set(getattr(self, "readonly_fields", []) or [])
        hidden = set(getattr(self, "hidden_fields", []) or [])
        blocked = readonly | hidden

        data: Dict[str, Any] = {}
        m2m_ops: List[Tuple[str, Iterable[Any] | None]] = []
        for name, fd in md.fields_map.items():
            if getattr(fd, "pk", False) or name in blocked:
                continue
            if isinstance(fd, ManyToManyFieldInstance):
                ids = payload.get(name, None if for_update else [])
                if ids is None:
                    if for_update:
                        m2m_ops.append((name, None))
                        continue
                    ids = []
                if not isinstance(ids, (list, tuple)):
                    ids = [ids]  # normalize str or single value
                m2m_ops.append((name, ids))
                continue
            if isinstance(fd, ForeignKeyFieldInstance):
                data[f"{name}_id"] = payload.get(name, None)
                continue
            if name in payload:
                val = payload[name]
                if (
                    val == ""
                    and (
                        getattr(fd, "nullable", False)
                        or getattr(fd, "null", False)
                    )
                    and isinstance(fd, (tfields.CharField, tfields.TextField))
                ):
                    val = None
                data[name] = val
        return data, m2m_ops

    async def save_create(
        self,
        request: Any,
        user: Any,
        md,
        payload: Dict[str, Any],
    ) -> Any:
        """Create a new model instance from ``payload``.

        ``request``, ``user`` and ``md`` are passed for symmetry with
        :meth:`save_update` and allow subclasses to take them into account.
        Foreign keys and many‑to‑many relations are handled automatically.
        Subclasses may override this to implement custom create behaviour.
        """

        data, m2m_ops = self.clean_payload(payload, for_update=False)
        obj = await self.model.create(**data)
        for fname, ids in m2m_ops:
            if ids is None:
                continue
            await obj.fetch_related(fname)
            manager = getattr(obj, fname)
            await manager.clear()
            if ids:
                await manager.add(*ids)
        return obj

    async def save_update(
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

        data, m2m_ops = self.clean_payload(payload, for_update=True)
        for key, val in data.items():
            setattr(obj, key, val)
        await obj.save()
        for fname, ids in m2m_ops:
            if ids is None:
                continue
            await obj.fetch_related(fname)
            manager = getattr(obj, fname)
            await manager.clear()
            if ids:
                await manager.add(*ids)
        return obj

    def get_list_columns(self, md) -> Sequence[str]:
        """Return column names used by list views.

        Defaults to :attr:`list_display` or the model's primary key.  Override
        this to supply custom dynamic column sets.
        """

        cols = list(self.list_display or [])
        if not cols:
            cols = [md.pk_attr]
        return cols

    def get_list_filters(self, md) -> List[Dict[str, Any]]:
        """Return filter specifications based on ``self.list_filter``.

        Each specification contains ``name``, ``label``, ``kind`` and allowed
        operations ``ops``. Choice fields include a ``choices`` list.
        """

        specs: List[Dict[str, Any]] = []
        if not self.list_filter:
            return specs

        fields = getattr(md, "fields", {}) or {}
        for item in self.list_filter:
            fname = item if isinstance(item, str) else None
            if not fname:
                continue
            fd = None
            if isinstance(fields, dict):
                fd = fields.get(fname)
            else:
                for f in fields:
                    if getattr(f, "name", None) == fname:
                        fd = f
                        break
            if fd is None:
                continue

            kind = getattr(fd, "kind", "")
            label = getattr(fd, "verbose_name", fname.replace("_", " ").title())

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
                "name": fname,
                "label": label,
                "kind": kind,
                "ops": ops,
            }
            if kind == "choice":
                spec["choices"] = [
                    {"value": v, "label": str(lbl)}
                    for v, lbl in getattr(fd, "choices", [])
                ]
            specs.append(spec)
        return specs

    def parse_filters(self, params, md):
        """
        Разбор query-параметров вида filter.<field>[__op]=value -> список (field, op, coerced_value)
        md: дескриптор модели (поля с типами), см. адаптер
        """
        filters = []
        for key, raw in params.items():
            if not key.startswith("filter."):
                continue
            frag = key[7:]
            if "__" in frag:
                fname, op = frag.split("__", 1)
            else:
                fname, op = frag, ""
            fd = None
            if hasattr(md, "fields"):
                try:
                    fd = md.fields.get(fname)
                except AttributeError:
                    for f in md.fields or []:
                        if getattr(f, "name", None) == fname:
                            fd = f
                            break
            if fd is None:
                fd = getattr(md, "fields_map", {}).get(fname)
            if fd is None:
                continue
            op = self.FILTER_OPS.get(op, "eq")
            val = self._coerce_value_for_filter(fd, raw, op)
            raw_txt = str(raw).strip().lower()
            if (val is not None) or (op == "eq" and raw_txt == "null"):
                filters.append((fname, op, val))
        return filters

    def _coerce_value_for_filter(self, fd, raw, op):
        """
        Приведение типов значения фильтра по описателю поля (fd.kind: 'string'|'integer'|'number'|'boolean'|'datetime'|'date' и т.д.)
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

    def apply_filters_to_queryset(self, qs, flist):
        """
        Применяем список фильтров к QuerySet (Tortoise ORM)
        """
        for fname, op, val in flist:
            if op == "eq":
                if isinstance(val, str) and val.lower() == "null":
                    qs = qs.filter(**{f"{fname}__isnull": True})
                else:
                    qs = qs.filter(**{fname: val})
            elif op == "icontains":
                qs = qs.filter(**{f"{fname}__icontains": val})
            elif op == "gte":
                qs = qs.filter(**{f"{fname}__gte": val})
            elif op == "lte":
                qs = qs.filter(**{f"{fname}__lte": val})
            elif op == "gt":
                qs = qs.filter(**{f"{fname}__gt": val})
            elif op == "lt":
                qs = qs.filter(**{f"{fname}__lt": val})
            elif op == "in":
                qs = qs.filter(**{f"{fname}__in": val})
        return qs

    def get_list_queryset(self, request, user, md, params: Dict[str, Any]) -> QuerySet:
        """Construct the queryset for list views.

        Applies searching, filtering and ordering. Row-level security is always
        enforced via :meth:`apply_row_level_security`. Foreign keys present in
        the list columns are eagerly loaded with ``select_related``. Subclasses
        may override to inject additional constraints.
        """

        search = params.get("search", "") or ""
        order = params.get("order", "")

        qs = self.get_base_queryset()
        qs = self.apply_row_level_security(qs, user)
        flist = self.parse_filters(getattr(request, "query_params", {}), md)
        qs = self.apply_filters_to_queryset(qs, flist)

        if search and self.search_fields:
            cond = None
            for sf in self.search_fields:
                lookup = f"{sf}__icontains"
                q_obj = Q(**{lookup: search})
                cond = q_obj if cond is None else (cond | q_obj)
            if cond is not None:
                qs = qs.filter(cond)

        if not order:
            if self.ordering:
                order = self.ordering[0]
            else:
                order = f"-{md.pk_attr}"

        columns = self.get_list_columns(md)
        sortable_keys = {c["key"] for c in self.columns_meta(md, columns) if c["sortable"]}
        ord_field = order[1:] if order.startswith("-") else order
        if ord_field not in sortable_keys:
            order = f"-{md.pk_attr}"
        qs = qs.order_by(order)
        params["order"] = order

        fk_to_select: List[str] = []
        fd_map = getattr(md, "fields_map", {})
        for col in columns:
            fd = fd_map.get(col)
            if fd and fd.relation and fd.relation.kind == "fk":
                fk_to_select.append(col)
        qs = self.apply_select_related(qs)
        # ``fk_to_select`` is appended after ``apply_select_related``
        if fk_to_select:
            qs = qs.select_related(*fk_to_select)

        qs = self.apply_only(qs, columns, md)
        if not isinstance(qs, QuerySet):  # pragma: no cover - runtime safety
            raise RuntimeError("get_list_queryset must return QuerySet")
        return qs


    async def serialize_list_row(self, obj: Any, md, columns: Sequence[str]) -> Dict[str, Any]:
        """Serialize ``obj`` for list output.

        Handles foreign keys and many‑to‑many values.  Override to customise
        serialization for list rows.
        """

        fd_map = getattr(md, "fields_map", {})
        row: Dict[str, Any] = {md.pk_attr: getattr(obj, md.pk_attr)}
        for col in columns:
            fd = fd_map.get(col)
            val = getattr(obj, col, None)
            if fd and fd.relation:
                try:
                    if fd.relation.kind == "fk":
                        rel_obj = getattr(obj, col)
                        row[col] = str(rel_obj) if rel_obj is not None else None
                    elif fd.relation.kind == "m2m":
                        try:
                            cnt = await getattr(obj, col).count()
                            row[col] = f"{cnt} items"
                        except Exception:
                            row[col] = None
                except Exception:
                    row[col] = None
            else:
                if val is not None and hasattr(val, "isoformat"):
                    row[col] = val.isoformat()
                else:
                    row[col] = val
        return row

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
            entry = {
                "key": col,
                "label": getattr(fd, "verbose_name", None)
                or col.replace("_", " ").title(),
                "type": _col_type(fd),
                "sortable": False
                if fd is None or (fd.relation and fd.relation.kind == "m2m")
                else True,
            }
            if fd and getattr(fd, "choices", None):
                ch_map = {}
                for ch in fd.choices:
                    try:
                        key, label = ch
                    except Exception:
                        key = getattr(ch, "value", ch)
                        label = getattr(ch, "label", str(ch))
                    ch_map[str(key)] = str(label)
                entry["choices_map"] = ch_map
            meta.append(entry)
        return meta


# The End

