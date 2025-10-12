# Architecture Overview

FreeAdmin is designed as a modular, layered system.  
Each layer has a single responsibility — and communicates through explicit, documented contracts.

This makes the framework both **predictable for developers** and **adaptable to any backend**.

---

## Core Layers

The system consists of four main layers:

```

                     ┌───────────────────────────────────────────┐
                     │                 Frontend                  │
                     │  HTML + Bootstrap 5 + Choices.js + jQuery │
                     │  JSONEditor widgets and AJAX actions      │
                     └───────────────────────────────────────────┘
                                          ▲
                                          │
                     ┌───────────────────────────────────────────┐
                     │               Admin Layer                 │
                     │   ModelAdmin, InlineAdmin, Cards, Views   │
                     │   Declarative definitions of UI logic     │
                     └───────────────────────────────────────────┘
                                          ▲
                                          │
                     ┌───────────────────────────────────────────┐
                     │                 Core Layer                │
                     │   AdminSite registry, routing, settings   │
                     │   Manages adapters and model discovery    │
                     └───────────────────────────────────────────┘
                                          ▲
                                          │
                     ┌───────────────────────────────────────────┐
                     │            Adapter / Connector            │
                     │  Bridges ORM, API, or data source logic   │
                     │  Provides CRUD interface and metadata     │
                     └───────────────────────────────────────────┘

````

---

## Layer Responsibilities

### 1. **Adapter / Connector Layer**
The lowest layer that connects FreeAdmin to a specific data source.

- Abstracts ORM operations (e.g., Tortoise ORM, SQLAlchemy)
- Exposes unified CRUD interface
- Normalizes model metadata for the admin layer
- Can be extended for APIs, remote services, or filesystems

Example:

```python
class TortoiseAdapter(BaseAdapter):
    def get_queryset(self, model):
        return model.all()

    def save(self, obj):
        await obj.save()
````

---

### 2. **Core Layer**

The central runtime of FreeAdmin — everything starts here.

Key components:

* `AdminSite`: manages registration of apps, models, and views
* `AdminSettings`: stores global configuration
* `AdminRouter`: handles URL routing and dispatch
* `Boot`: initializes registry and loads extensions

The Core Layer provides the infrastructure for your admin to **discover**, **configure**, and **serve** all registered modules.

---

### 3. **Admin Layer**

Defines *what* appears in the interface and *how* it behaves.

* `ModelAdmin` and `InlineAdmin` describe model behavior (columns, filters, forms)
* `Card`, `View`, and `Action` define higher-level UI constructs
* Permissions and roles can be applied per model or globally

Example:

```python
class ProductAdmin(ModelAdmin):
    list_display = ["name", "price", "available"]
    search_fields = ["name"]
    ordering = ["name"]
```

Each class in this layer is **pure metadata** — no rendering or database logic.

---

### 4. **Frontend Layer**

The visual part of FreeAdmin, implemented with minimal dependencies:

* **Bootstrap 5.3** for layout and theme
* **Choices.js** for advanced selects
* **JSONEditor** for dynamic forms
* **jQuery** for interaction and AJAX
* **JSBarcode** for barcode widgets

Front-end components are declarative — rendered dynamically from metadata provided by the Admin Layer.

Example:

```html
<select data-widget="choices" data-source="/api/products/"></select>
```

---

## Runtime Flow

1. **Boot Phase** — `AdminSite.boot()` loads all registered modules.
2. **Discovery** — AdminSite scans apps and imports `admin.py`.
3. **Registry Setup** — Each `ModelAdmin` registers itself with the site.
4. **Routing** — URLs are built dynamically for registered views.
5. **Serving** — Requests are handled via adapters, and results are rendered via widgets.

---

## Modularity in Action

Each layer can be replaced or extended:

* Write a custom **Adapter** to support a new ORM.
* Override **AdminRouter** to integrate with your FastAPI app.
* Add a new **Widget** or **Card** type to enrich the UI.
* Create **Custom Boot hooks** to inject logic during startup.

This modularity allows you to start small — with one model and one admin — and grow into a complete, enterprise-grade admin system.

