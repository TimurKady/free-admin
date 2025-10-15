# Models and Admin Models

This guide walks through the journey from defining database models to exposing
them inside the FreeAdmin interface. The focus is on providing context-rich
explanations so you can understand **why** each piece matters before you copy a
line of code.

FreeAdmin keeps a clean separation between two layers:

1. **ORM models** describe your data schema and business rules.
2. **Admin descriptors** (`ModelAdmin` and `InlineModelAdmin`) describe how
   those models are presented, searched, filtered, and mutated inside the
   administration UI.

Because the admin layer is thin, you can bring your own asynchronous ORM. The
examples below use Tortoise ORM, but the APIs highlighted here mirror the
adapter contracts implemented in `freeadmin.core.interface.base.BaseModelAdmin`.


## Defining an ORM model

You start by declaring ordinary ORM models. The admin site only requires that
the adapter can introspect fields and execute async CRUD operations.

```python
# apps/catalog/models.py
from tortoise import fields
from tortoise.models import Model


class Product(Model):
    """Minimal Tortoise model used throughout the examples below."""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    available = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "catalog_product"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
```

> **Narrative tip.** Choose descriptive `Meta.table` values and implement
> `__str__`. FreeAdmin reuses them when it renders relation widgets, inline
> badges, and selection lists.

## Registering models with the admin site

Once the model exists you hook it into the global admin site. The admin hub is
exposed through `freeadmin.hub.admin_site`. Registration wires together the
model class, its admin descriptor, menu metadata, and the adapter used to talk
to your database.

```python
# apps/catalog/admin.py
from freeadmin.core.interface.models import ModelAdmin
from freeadmin.hub import admin_site

from .models import Product


class ProductAdmin(ModelAdmin):
    """List, search, and edit catalog products."""

    list_display = ("id", "name", "price", "available")
    search_fields = ("name",)
    ordering = ("name",)


admin_site.register(app="catalog", model=Product, admin_cls=ProductAdmin)
```

* `app` becomes the slug visible in URLs (`/admin/orm/catalog/product/`).
* `model` is the ORM class itself.
* `admin_cls` is instantiated lazily by `AdminSite.register()` and receives the
  adapter defined by the boot process.
* Optional keyword arguments let you publish the descriptor under
  `/admin/settings/…` (`settings=True`) or register it in both menus at once via
  `admin_site.register_both()`.

Registration normally lives in the app’s `admin.py` so that import side effects
are predictable. If you prefer structured startup logic, wrap the registration
inside an `AppConfig.startup()` method and import the config in your boot
sequence.


## What a `ModelAdmin` does for you

`ModelAdmin` subclasses inherit a long list of sensible defaults from
`BaseModelAdmin`. You only override the pieces you want to surface.

### Essential attributes

| Attribute            | Purpose | Story behind it |
| -------------------- | ------- | --------------- |
| `label` / `label_singular` | Override the plural and singular captions shown in menus and headers. | Set them when the automatically generated names (`Product` → `Products`) do not read naturally. |
| `list_display`       | Tuple of column names or callables. | Defaults to every non-primary-key field so the changelist stays informative even if you omit it. |
| `search_fields`      | Tuple of field names. | If empty, `BaseModelAdmin` inspects your descriptor and automatically includes `CharField`/`TextField` columns without choices. |
| `list_filter`        | Tuple of dot-separated paths. | Each entry becomes a sidebar filter; related paths such as `"category.name"` are resolved recursively. |
| `ordering`           | Default ordering sent to the adapter. | Falls back to the model’s primary key when not provided. |
| `fields`             | Controls the form layout. | When omitted every non-readonly field is shown, honouring `readonly_fields` and implicit defaults. |
| `readonly_fields`    | Tuple of field names shown as read-only widgets. | Useful for audit fields and computed data. |
| `autocomplete_fields`| Enables AJAX autocompletion for foreign keys. | FreeAdmin converts matching widgets to async search inputs. |
| `actions`            | Tuple of subclasses of `BaseAction`. | Defaults to `DeleteSelectedAction` and `ExportSelectedAction`. |

### Enriching the list view with callables

You can add computed columns by defining methods that accept the row object.

```python
class ProductAdmin(ModelAdmin):
    list_display = ("id", "name", "price_tag", "available")

    def price_tag(self, obj) -> str:
        """Format the price including a currency symbol."""

        return f"${obj.price:.2f}"
```

`BaseModelAdmin` automatically detects these callables and exposes them through
the metadata API used by the React front end.

### Customising querysets and permissions

Every CRUD operation flows through async hooks that you may override:

* `get_queryset(request, user)` – tweak the base queryset before list
  operations run.
* `apply_row_level_security(qs, user)` – enforce per-user filters reused across
  list, detail, and inline operations.
* `allow(user, action, obj=None)` – control per-action UI affordances. The base
  implementation already checks `PermAction` flags and superuser status.

These hooks live in `BaseModelAdmin`, so refer to the inline documentation for
finer details before overriding them.

## Inline editors with `InlineModelAdmin`

Inline descriptors let users edit related rows without leaving the parent form.
Create a subclass of `freeadmin.core.interface.inline.InlineModelAdmin`, set its `model`
and tell FreeAdmin which foreign key links it to the parent via
`parent_fk_name`.

```python
from freeadmin.core.interface.inline import InlineModelAdmin

from .models import Product, ProductImage


class ProductImageInline(InlineModelAdmin):
    """Manage product imagery alongside the product form."""

    model = ProductImage
    parent_fk_name = "product"
    list_display = ("image", "alt_text")
    can_delete = True
    collapsed = False


class ProductAdmin(ModelAdmin):
    inlines = (ProductImageInline,)
```

The admin site instantiates inline classes on demand, injects the same adapter
used by the parent admin, and surfaces a metadata payload describing columns,
permissions, and badge counts. Advanced behaviour such as forced foreign key
headers (`X-Force-FK-<field>`) is already handled inside `BaseModelAdmin.create`
and `BaseModelAdmin.update`, so inline POST/DELETE requests remain minimal.

## Bulk actions

Actions are class-based and inherit from `freeadmin.core.interface.actions.BaseAction`.
They receive a queryset (or iterable compatible with your adapter), a params
dictionary, and the current user. Returning an `ActionResult` communicates the
outcome back to the UI.

```python
from freeadmin.core.interface.actions import ActionResult, ActionSpec, BaseAction


class MarkUnavailableAction(BaseAction):
    """Flag selected products as unavailable."""

    spec = ActionSpec(
        name="mark_unavailable",
        label="Mark as unavailable",
        description="Set the availability flag to false",
        danger=False,
        scope=["change"],
        params_schema={},
        required_perm=None,
    )

    async def run(self, qs, params, user) -> ActionResult:
        """Update each selected product and report how many rows changed."""

        rows = await self.admin.adapter.fetch_all(qs)
        for obj in rows:
            obj.available = False
            await self.admin.adapter.save(obj)
        return ActionResult(ok=True, affected=len(rows))


class ProductAdmin(ModelAdmin):
    actions = ModelAdmin.actions + (MarkUnavailableAction,)
```

You can also reuse the built-in `DeleteSelectedAction` and
`ExportSelectedAction`. The adapter wrapper exposes conveniences like
`fetch_all`, `assign`, and queryset builders (`filter`, `order_by`), so writing
async-friendly actions is a matter of orchestrating your domain logic.


## Working with enums and choice fields

`BaseModelAdmin.get_list_filters()` recognises the `choices` metadata exposed by
your ORM descriptor. When a field exposes `choices` or derives from
`CharEnumField`, FreeAdmin renders the widget as a select box automatically.

```python
import enum


class Product(Model):
    class Status(str, enum.Enum):
        ACTIVE = "active"
        ARCHIVED = "archived"

    status = fields.CharEnumField(enum_type=Status, default=Status.ACTIVE)


class ProductAdmin(ModelAdmin):
    list_filter = ("status",)
```

The filter sidebar receives the enum values and their display labels; form
widgets display the same readable names. No extra wiring is required as long as
your adapter exposes `choices` in its model descriptor.


## Relations and search paths

Foreign keys and many-to-many relations are processed automatically by the base
class. You can reference related fields in `list_display`, `list_filter`, and
`search_fields` by using Django-style double underscores (e.g.
`"category__name"`). The admin site resolves these lookups when it builds the
filter specification.

```python
class Category(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)


class Product(Model):
    category = fields.ForeignKeyField("models.Category", related_name="products")


class ProductAdmin(ModelAdmin):
    list_display = ("name", "category")
    search_fields = ("name", "category__name")
    list_filter = ("category",)
```

When a user edits a product, FreeAdmin renders the `category` field as a select
widget, populated through the adapter’s metadata APIs. Many-to-many widgets are
handled in the same fashion, including add/remove semantics during save.


## Putting it all together

Here is a compact directory layout to demonstrate how the components fit.

```
apps/catalog/
├── __init__.py
├── admin.py
├── app.py
└── models.py
```

**models.py**

```python
from tortoise import fields
from tortoise.models import Model


class Category(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)


class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    category = fields.ForeignKeyField("models.Category", related_name="products")
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    available = fields.BooleanField(default=True)
```

**admin.py**

```python
from freeadmin.core.interface.inline import InlineModelAdmin
from freeadmin.core.interface.models import ModelAdmin
from freeadmin.hub import admin_site

from .models import Category, Product


class ProductInline(InlineModelAdmin):
    """Show products inside the category form."""

    model = Product
    parent_fk_name = "category"
    list_display = ("name", "price", "available")


class CategoryAdmin(ModelAdmin):
    """Manage catalog categories."""

    list_display = ("name",)
    inlines = (ProductInline,)


class ProductAdmin(ModelAdmin):
    """Manage catalog products."""

    list_display = ("name", "category", "price", "available")
    list_filter = ("category", "available")
    search_fields = ("name", "category__name")


admin_site.register(app="catalog", model=Category, admin_cls=CategoryAdmin)
admin_site.register(app="catalog", model=Product, admin_cls=ProductAdmin)
```

**app.py**

```python
from freeadmin.core.interface.app import AppConfig


class CatalogConfig(AppConfig):
    """Make the catalog package discoverable by the boot manager."""

    app_label = "catalog"
    name = "myproject.apps.catalog"


default = CatalogConfig()
```

Importing `apps.catalog.admin` anywhere in your startup path completes the
picture: models are available to FreeAdmin, the admin site understands how to
list them, inline editors surface related data, and default bulk actions are
ready. From there you can layer in custom permissions, bespoke widgets, or
domain-specific actions by extending the documented hooks.

## Summary

* Define plain ORM models – the adapter handles metadata and CRUD.
* Create `ModelAdmin` subclasses to describe how the admin UI should present
  those models.
* Register models with `admin_site.register()` (or `register_both()` when you
  need both ORM and Settings menus).
* Use `InlineModelAdmin` to embed related rows.
* Extend bulk behaviour with `BaseAction` subclasses.
* Let FreeAdmin’s defaults carry the heavy lifting while you focus on domain
  rules and user experience.

