# Core Concepts and Terminology

Before building your first admin interface, it’s important to understand the key abstractions that form the foundation of FreeAdmin.


## AdminSite

The **AdminSite** is the central registry and runtime environment for all admin components.

It manages:
- model and view registration
- adapter configuration
- routing and boot sequence
- system-wide settings

Typical usage:

```python
from freeadmin import AdminSite
from myapp.models import Product
from myapp.admin import ProductAdmin

site = AdminSite(title="My Admin")
site.register(Product, ProductAdmin)
site.run()
````

Think of it as the *root object* that holds your entire admin definition.

---

## ModelAdmin

A **ModelAdmin** describes how a data model is displayed and edited in the admin interface.
It defines table columns, filters, search fields, forms, and actions.

Example:

```python
from freeadmin import ModelAdmin

class ProductAdmin(ModelAdmin):
    list_display = ["name", "price", "available"]
    search_fields = ["name"]
    ordering = ["name"]
```

ModelAdmin never touches your ORM directly — it delegates data operations to an **Adapter**.

---

## InlineAdmin

An **InlineAdmin** allows editing of related models directly within another model’s form.

Example:

```python
class ProductImageInline(InlineAdmin):
    model = ProductImage
    fields = ["image", "alt_text"]
```

You register inlines inside a parent `ModelAdmin`:

```python
class ProductAdmin(ModelAdmin):
    inlines = [ProductImageInline]
```

---

## Adapter (or Connector)

An **Adapter** (sometimes referred to as a *Connector*) bridges the admin system with your data layer.
It defines the CRUD operations and metadata extraction.

Each Adapter implements a unified interface:

```python
class BaseAdapter:
    def get_queryset(self, model): ...
    def get_object(self, model, pk): ...
    def save(self, obj): ...
    def delete(self, obj): ...
```

Currently, the built-in adapters support **Tortoise ORM**. An adapter for **SQLAlchemy** will be added in the future, but you can easily add your own adapters right now.

---

## AdminRouter

The **AdminRouter** is responsible for URL dispatching and endpoint mapping.

It automatically builds URLs for each registered model and view, e.g.:

```
/admin/products/
/admin/products/add/
/admin/products/1/change/
/admin/settings/
```

Routers can be overridden or extended for integration with frameworks like FastAPI or Starlette.

---

## Boot

The **Boot** process initializes FreeAdmin:
it loads settings, imports `admin.py` modules, registers models, and prepares the UI.

Example:

```python
site.boot()
```

Boot hooks can be added to inject custom logic during startup (logging, extensions, etc.).

---

## Card

A **Card** is a visual block displayed on dashboard pages or model views.
Cards are used to present summaries, metrics, or custom HTML widgets.
The advantage of cards is the ability to display changes in parameters in real time.

Example:

```python
from freeadmin import Card

class SalesOverview(Card):
    title = "Monthly Sales"
    template = "cards/sales_overview.html"
```

You can register cards globally or per model.

---

## View

A **View** defines a custom page or endpoint within the admin interface.
It extends the core UI with domain-specific functionality.

Example:

```python
from freeadmin import View

class ImportDataView(View):
    path = "import-data"
    template = "admin/import_data.html"

    async def post(self, request):
        ...
```

Views can be bound to menu items or triggered from actions.
Your views can integrate various JS scripts and CSS tables.

---

## Action

An **Action** represents an operation that can be executed on selected objects in a list view.

Example:

```python
def mark_as_featured(request, queryset):
    queryset.update(featured=True)

class ProductAdmin(ModelAdmin):
    actions = [mark_as_featured]
```

Actions can be synchronous or asynchronous, and may require user confirmation.

---

## Widget

A **Widget** is a frontend component that renders a field or UI element.

Widgets are defined declaratively and powered by JavaScript libraries such as:

* **Select2** (dropdown with autocomplete)
* **Choices.js** (dropdowns)
* **JSONEditor** (complex forms)
* **JSBarcode** (barcode fields)

Example:

```python
widgets = {
    "category": "select2",
    "metadata": "json-editor"
}
```

---

## Settings

**AdminSettings** store system-wide configuration such as titles, themes, and feature flags.

```python
site.settings.update(
    title="FreeAdmin Demo",
    theme="light",
    locale="en"
)
```

Settings can also be changed dynamically via the admin UI.

---

## Key Takeaway

FreeAdmin separates **definition**, **data**, and **presentation**:

* **Definition:** what the admin should do (ModelAdmin, Card, View)
* **Data:** how it talks to storage (Adapter)
* **Presentation:** how it looks and behaves (Widgets, Frontend)

This separation keeps the system simple, testable, and endlessly extensible.


