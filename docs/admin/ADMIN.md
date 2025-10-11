# Admin Panel Architecture

This document outlines the layered architecture of the Cortex admin panel. The system is designed to separate pure metadata from framework-specific adapters and UI widgets.

See [System Settings](admin/settings.md) for configurable keys and default values.

## 1. Core: Declarative Admin Model

The **Core** layer defines the pure admin model without any front‑end dependencies.

- `AdminSite` handles model registration and global configuration.
- `ModelAdmin` exposes declarative options similar to Django, such as:
  - `list_display`, `list_filter`, `search_fields`
    - `list_filter` must be defined explicitly; otherwise no filter UI or
      "Filters" button is rendered.
    - If `list_display` is omitted, table columns are derived on the client
      side using the fields from `ModelAdmin.get_fields`.
  - `formfields_overrides`, `inlines`
  - `ordering`, `readonly_fields`, `autocomplete_fields`, `raw_id_fields`
    - `autocomplete_fields` activates `RelationsWidget` with remote lookup,
      allowing relational fields to be searched on demand instead of
      preloading choices. Keep lookup pages small (around 25 results) to
      reduce server load.
  - custom actions and more.
- Only rules and metadata are defined here; no UI logic is included.

## 2. Adapters: ORM and Web Integration

Adapters translate Core metadata to specific frameworks.

- **TortoiseAdapter** extracts field types, relations (FK/M2M) and choice values, exposing unified field descriptors.
- **FastAPIAdapter** builds API endpoints from Core metadata. It focuses solely on input/output serialization and validation without assuming any front‑end library.
- **RelationsWidget / Select2Widget** share a mixin (`RelationPrefetchMixin`) that preloads relation choices via `ModelAdmin.get_choices(field_name)` and stores them in `FieldDescriptor.meta`. Filtering logic lives in `get_choices()`, not in request parameters, and the prefetch step prepares a `choices_map` so widgets operate without extra ORM queries.

## 3. Schema: Form Generation

`ModelAdmin` exposes a single hook for form generation:
`get_schema` returns a plain JSON Schema plus initial values.

- `get_schema` must not use `oneOf`; widgets expect a single `type` and optional
  `enum`/`enum_titles` pairs. Optional FK fields expose a placeholder entry via
  `options.has_placeholder_option` (with text from `placeholder_option_text`)
  instead of embedding a dummy enum value.
- For FK/M2M fields: set `type: string` or `array` in JSON Schema and use
  `format` or `options` keys to influence rendering.
- Date and datetime fields define their basic type and `format` in JSON Schema.

## 4. Widgets: Pure Widget Layer

Widgets handle front‑end initialization only and are registered on the server
with a unique key.

- Widgets focus on JSON Schema fragments and may supply start values when
  necessary. Any JavaScript or CSS assets are loaded statically by the template
  system.
- See [built-in widgets](admin/widgets.md) for examples such as `TextWidget`,
  `ChoicesWidget`, and `TextAreaWidget`.

## 5. Templates: Thin Rendering Layer

Templates remain minimal and do not embed business logic.

- A base template and a single form template load JSONEditor and the form script; the editor fetches `{schema, startval}` from the API.
- See [Front‑end assets and plugins](admin/frontend.md) for how shared libraries are included.

This modular design enables gradual migration and keeps the admin panel maintainable while avoiding tight coupling with specific front‑end tools.

## Permission Codenames

Permissions are addressed using a dotted codename of the form `app.model.action`.

- `app` – application label used when registering a model with the admin site
- `model` – lowercase model class name used as slug (e.g., `StreamGraph` → `streamgraph`)
- `action` – one of `view`, `add`, `change` or `delete`

These codenames are checked by `require_permissions` to ensure the current user has the necessary rights for the given content type.

