# ModelAdmin contract

## Authorization
Access to endpoints is handled via dependency injection (RBAC). ModelAdmin does **not** perform authorization.

## Core attributes

- `label` — plural model name used in menus and headings. See [`BaseModelAdmin.get_label`](../../contrib/admin/core/base.py#L166-L168).
- `list_display` — columns shown in list view. See [`BaseModelAdmin.get_list_display`](../../contrib/admin/core/base.py#L174-L176).
- `search_fields` — fields searched by the list search box. See [`BaseModelAdmin.get_search_fields`](../../contrib/admin/core/base.py#L842-L863).
- `list_filter` — sidebar filters for list view. See [`BaseModelAdmin.get_list_filter`](../../contrib/admin/core/base.py#L178-L180).
- `ordering` — default ordering of results. See [`BaseModelAdmin.get_ordering`](../../contrib/admin/core/base.py#L182-L193).
- `fieldsets` — groups of form fields represented as a list of dictionaries with:
  - `title` — heading displayed for the group.
  - `icon` — Bootstrap icon class rendered before the title.
  - `hide_title` — hides the heading; alternatively set `title="\u200B"`.
  - `class` — extra CSS classes on the fieldset wrapper.
  - `collapsed` — enable the collapse toggle. Groups default to a collapsed state unless you explicitly set `False`; omit the key to hide the toggle entirely.
  - `fields` — ordered fields or tuples of fields.
  Icons render via `<i class="bi {icon}"></i>` and titles can be suppressed with the zero-width space `"\u200B"`. See [`BaseModelAdmin.get_fieldsets`](../../contrib/admin/core/base.py#L567-L586).
- `fields` — explicit form field order. See [`BaseModelAdmin.get_fields`](../../contrib/admin/core/base.py#L515-L567).
- `readonly_fields` — fields rendered as read-only. See [`BaseModelAdmin.get_readonly_fields`](../../contrib/admin/core/base.py#L195-L197).
- `autocomplete_fields` — fields using autocomplete widgets. See [`BaseModelAdmin.get_autocomplete_fields`](../../contrib/admin/core/base.py#L199-L201) and [`get_autocomplete_queryset`](../../contrib/admin/core/base.py#L461-L482).

```python
from freeadmin.core.interface.models import ModelAdmin
from freeadmin.core.runtime.hub import admin_site
from apps.authors.models import Author


class AuthorAdmin(ModelAdmin):
    fieldsets = [
        {
            "title": "Author",
            "icon": "bi-person-badge",
            # basic author profile
            "fields": ["full_name", "photo", "bio", "is_active"],
        },
        {
            # no text — icon-only header
            "title": "\u200B",
            "icon": "bi-columns-gap",
            "hide_title": True,
            "class": "two-cols",  # the compiler turns this into a 2×N grid
            # tuples = grid rows; items inside a tuple are cells
            "fields": [
                ("email", "phone", "website", "city"),
                ("books_count", "rating"),
                ("created_by", "created_at"),
            ],
        },
        {
            "title": "Social",
            "icon": "bi-share",
            "collapsed": True,
            "fields": ["twitter", "instagram", "facebook", "youtube"],
        },
    ]


admin_site.register(app="authors", model=Author, admin_cls=AuthorAdmin)

```

## Static assets

- `admin_assets_css` — tuple of global CSS asset paths. They are merged with widget assets in [`BaseModelAdmin.collect_assets`](../../contrib/admin/core/base.py#L389-L417).
- `admin_assets_js` — tuple of global JavaScript asset paths, also processed by [`collect_assets`](../../contrib/admin/core/base.py#L389-L417).
- `widgets_overrides` — mapping `{field: widget_key}` assembled from `Meta.widgets` or `widgets` and applied by [`BaseModelAdmin._resolve_widget_key`](../../contrib/admin/core/base.py#L578-L584) to override default widgets. Binary model fields (`BinaryField`) are excluded from forms unless their widget is defined explicitly.

Widgets can be provided as registry keys, widget classes, or pre‑instantiated objects. When an instance is supplied, `BaseModelAdmin` attaches the form context and reuses the same object, preserving any configuration.

```python
from freeadmin.core.interface.models import ModelAdmin
from freeadmin.contrib.widgets import TextWidget, TextAreaWidget


class PostAdmin(ModelAdmin):
    widgets = {
        "email": TextWidget(format="email"),
        "body": TextAreaWidget(
            format="markdown",
            options={"simplemde": {"toolbar": ["bold", "italic"]}},
        ),
    }
```

During form construction [`BaseModelAdmin._build_widget`](../../contrib/admin/core/base.py#L745-L749) detects these instances and preserves them by setting `ctx` on the existing object.

> **Note**
> Provide a widget override for a `BinaryField` in `widgets` or `Meta.widgets` to include it in the form.

## QuerySet hooks (all must return a QuerySet)
- `get_queryset()` -> QuerySet (typically `model.all()`)
- `get_list_queryset(request, user)` -> QuerySet
  = base -> `apply_select_related` -> `apply_only` -> `apply_row_level_security`
- `get_objects(request, user)` -> QuerySet
  = base -> `apply_select_related` -> `apply_row_level_security`
- `form_queryset(md, mode, qs=None)` -> QuerySet
  = `all()` -> `select_related` -> `prefetch_related`
- `apply_select_related(qs)` -> QuerySet
- `apply_only(qs)` -> QuerySet
- `apply_row_level_security(qs, user)` -> QuerySet (RLS)

## Business constraints (UI)
- `allow(user, action, obj=None)` -> bool
Used to hide buttons, set fields read-only, or apply soft business validation (403/422).
Does **not** replace RBAC.

## Actions
Administrative actions live in `contrib/admin/core/actions`. The package defines the
`BaseAction` interface and an `ActionSpec` describing each action's name, label,
parameters, and risk level. Parameter types are expressed as strings such as
"boolean" or "string". Actions operate on querysets in batches and may be
reused across different admins.

### `ModelAdmin.actions`, `list_actions`, `get_action` and `get_actions`
`ModelAdmin.actions` holds a tuple of available action classes. By default it
includes `DeleteSelectedAction`. Use `list_actions()` to enumerate action
names and `get_action(name)` to retrieve a bound instance. The
`get_actions()` method instantiates all actions and returns a dictionary
mapping each action's `spec.name` to the corresponding instance for bulk
access. Action names must be unique; duplicates raise ``ValueError``.

### `DeleteSelectedAction`
Removes all objects from the queryset after confirmation.

- **spec.name**: `delete_selected`
- **scope**: `['ids', 'query']`
- **params**: `{"confirm": "boolean"}` — must be `True` to proceed

```python
result = await admin.perform_action(
    "delete_selected", queryset, {"confirm": True}, user
)
```

> **Note**
> Always require explicit confirmation before executing destructive actions.

## QuerySet contract
1. Every QuerySet hook must return a QuerySet.
2. `get_list_queryset` is built as `base → apply_select_related → apply_only → apply_row_level_security`.
3. `get_objects` is built as `base → apply_select_related → apply_row_level_security`.
4. `apply_row_level_security` is always executed last.
5. Returning a non-QuerySet raises `RuntimeError`.

## form_queryset and get_object

`form_queryset` builds the base QuerySet for form operations. By default it calls `all()` on the model and automatically adds `select_related` for foreign keys and `prefetch_related` for many-to-many relations. The method can be overridden to extend the selection:

```python
class BookAdmin(ModelAdmin):
    def form_queryset(self, md, mode, qs=None):
        qs = super().form_queryset(md, mode, qs)
        return qs.select_related("author").prefetch_related("tags")
```

`get_object` uses `get_objects` → `form_queryset` and returns an object via `get`/`aget`. Overriding allows custom retrieval logic:

```python
async def get_object(self, request, md, mode, user):
    obj = await super().get_object(request, md, mode, user)
    # additional processing
    return obj
```

## RLS invariants
- `get_list_queryset` and `get_objects` must apply `apply_row_level_security`.
- In `get_schema(mode="edit")` the object is retrieved through `get_objects(...)` (RLS).
- `has_view/add/change/delete_permission` methods have been removed.

