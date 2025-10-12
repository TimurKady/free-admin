# Models and Admin Models

This section explains how to define database models and configure their administrative interfaces using `ModelAdmin` and `InlineAdmin`.

FreeAdmin separates **data definition** (models) from **presentation logic** (admin classes).  
You define your models using your ORM (e.g. Tortoise ORM), and then describe how they appear and behave in the admin interface.


## Defining a Model

Models describe your data structure — tables, fields, and relations.  
FreeAdmin supports any ORM that provides metadata and async CRUD operations.  
The examples below use **Tortoise ORM**.

Example:

```python
# apps/products/models.py
from tortoise import fields
from tortoise.models import Model

class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    available = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "product"
        ordering = ["name"]

    def __str__(self):
        return self.name
````

> **Tip:**
> Every model should have a `Meta` class with `table` name and default `ordering`.
> Use `__str__` to define how the object appears in dropdowns and relation fields.


## Registering Models in the Admin

Once the model is defined, you must **register** it with FreeAdmin.

Each app has its own `app.py` file that defines an `AppConfig`.
Inside `ready()`, register your model and its admin definition:

```python
# apps/products/app.py
from freeadmin import AppConfig
from .models import Product
from .admin import ProductAdmin

class ProductsConfig(AppConfig):
    app_label = "products"
    name = "apps.products"

    def ready(self):
        self.register(Product, ProductAdmin)

default = ProductsConfig()
```

## Creating a ModelAdmin

`ModelAdmin` controls how a model appears in the admin interface:
columns, filters, search fields, ordering, and actions.

Example:

```python
# apps/products/admin.py
from freeadmin import ModelAdmin
from .models import Product

class ProductAdmin(ModelAdmin):
    list_display = ["name", "price", "available"]
    search_fields = ["name"]
    list_filter = ["available"]
    ordering = ["name"]
    per_page = 25
```

| Attribute           | Type      | Description                    |
| ------------------- | --------- | ------------------------------ |
| **`list_display`**  | list[str] | Columns shown in the list view |
| **`search_fields`** | list[str] | Fields used for search         |
| **`list_filter`**   | list[str] | Sidebar filters                |
| **`ordering`**      | list[str] | Default order                  |
| **`per_page`**      | int       | Pagination limit               |

---

## InlineAdmin

`InlineAdmin` lets you edit related objects directly inside the parent form.

Example:

```python
# apps/products/admin.py
from freeadmin import InlineAdmin
from .models import ProductImage

class ProductImageInline(InlineAdmin):
    model = ProductImage
    fields = ["image", "alt_text"]
```

Attach it to your `ModelAdmin`:

```python
class ProductAdmin(ModelAdmin):
    list_display = ["name", "price", "available"]
    inlines = [ProductImageInline]
```

> InlineAdmins automatically manage foreign key relations and nested saving logic.

---

## Actions

Actions are operations you can perform on multiple selected objects.
They can be defined as plain functions or class-based methods.

Example:

```python
def mark_as_unavailable(request, queryset):
    queryset.update(available=False)

class ProductAdmin(ModelAdmin):
    list_display = ["name", "price", "available"]
    actions = [mark_as_unavailable]
```

For confirmation dialogs or async execution, you can use advanced Action APIs (see the *Advanced Usage* section).

---

## Choices and Enums

FreeAdmin automatically converts Python Enums or `choices` into dropdown fields.

Example:

```python
from tortoise import fields

class Product(Model):
    class Status:
        ACTIVE = "active"
        ARCHIVED = "archived"

        CHOICES = [
            (ACTIVE, "Active"),
            (ARCHIVED, "Archived"),
        ]

    status = fields.CharEnumField(choices=Status.CHOICES, default=Status.ACTIVE)
```

In the admin form, this field will appear as a **select box** automatically.

---

## Display Methods

You can add computed or formatted columns to your list view by defining methods on your `ModelAdmin`.

```python
class ProductAdmin(ModelAdmin):
    list_display = ["name", "price_with_currency", "available"]

    def price_with_currency(self, obj):
        return f\"${obj.price:.2f}\"
```

> **Note:** These methods must accept one argument (`obj`) and return a string or HTML-safe value.

---

## Related Models and Foreign Keys

ForeignKey and ManyToMany relations are rendered automatically as dropdowns or multi-selects, depending on field type.

Example:

```python
class Category(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)

class Product(Model):
    category = fields.ForeignKeyField("models.Category", related_name="products")
```

Admin:

```python
class ProductAdmin(ModelAdmin):
    list_display = ["name", "category"]
    search_fields = ["name", "category__name"]
```

---

## Example: Full Application

```
apps/products/
├── app.py
├── models.py
├── admin.py
└── __init__.py
```

**models.py**

```python
class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    category = fields.ForeignKeyField("models.Category", related_name="products")
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    available = fields.BooleanField(default=True)
```

**admin.py**

```python
class ProductAdmin(ModelAdmin):
    list_display = ["name", "category", "price", "available"]
    list_filter = ["category", "available"]
    search_fields = ["name", "category__name"]
```

**app.py**

```python
class ProductsConfig(AppConfig):
    def ready(self):
        self.register(Product, ProductAdmin)
```

---

## Summary

| Concept             | Description                             |
| ------------------- | --------------------------------------- |
| **Model**           | Defines data schema                     |
| **ModelAdmin**      | Defines admin presentation              |
| **InlineAdmin**     | Manages related models                  |
| **Actions**         | Adds bulk operations                    |
| **Choices / Enums** | Converts constants into dropdowns       |
| **Foreign Keys**    | Automatically rendered as select fields |


