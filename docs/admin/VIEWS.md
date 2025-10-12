# Admin Views

Admin views extend the Cortex admin panel with pages that are not backed by ORM models. They share the
same layout, navigation, and authentication stack as CRUD pages while letting you mount dashboards,
reports, or custom workflows implemented as FastAPI callables.

## Core concepts

`AdminSite.register_view()` is the entry point for declaring a standalone page. When you decorate a
callable with it, the site stores sidebar metadata, wires the handler into the routing table, and
wraps it as a `FreeViewPage` so the shared template context is always available.【F:contrib/admin/core/site.py†L586-L660】

Each view exposes the following pieces of data:

- **path** – URL relative to the admin base; it must include the `/views/<app>/<slug>/` tail so the
  sidebar can deduce the owning application.【F:contrib/admin/core/site.py†L607-L651】
- **name** – human-readable title displayed in breadcrumbs and sidebar entries.【F:contrib/admin/core/site.py†L646-L660】
- **label** – optional explicit application label used for grouping; when omitted, the label is
  deduced from the path prefix.【F:contrib/admin/core/site.py†L601-L621】
- **icon** – optional Bootstrap icon class used in navigation and menus.【F:contrib/admin/core/site.py†L646-L660】
- **settings** – flag that reuses the settings prefix and keeps the view under the settings section.

Besides the runtime handler, the site records a `_ViewRoute` structure with the normalized path,
app slug, model slug, and settings flag. This metadata powers breadcrumbs and helps
`AdminSite.build_template_ctx()` mark the current navigation entry.【F:contrib/admin/core/site.py†L628-L660】

## Virtual metadata and registry

All views are tracked inside `PageRegistry`. Whenever a view is registered, the registry emits a
`VirtualContentKey` entry that stores stable app and slug identifiers. The admin site reuses this
virtual metadata for menu items, cards, and permissions to ensure consistency across sessions and
process restarts.【F:contrib/admin/core/registry.py†L54-L140】【F:contrib/admin/core/registry.py†L189-L220】

The registry enforces idempotency: attempts to register the same `(app, slug, settings)` pair are
ignored, while collisions with different data raise `ValueError`. This protects existing routes from
being overridden silently.【F:contrib/admin/core/registry.py†L85-L139】

## Sidebar integration

`AdminSite` keeps a `_views` dictionary that mirrors the sidebar hierarchy. Each entry contains the
model-style slug, display name, path, icon, and a `settings` flag. When the template builder runs, it
converts this structure into `{label: [entries...]}` records so the sidebar can show models and views
side-by-side. Tests assert that only registered views appear in this collection and that the current
route is highlighted correctly.【F:contrib/admin/core/site.py†L646-L688】【F:tests/test_views_sidebar.py†L1-L162】

Views that live directly under `/views/` act as landing pages and can opt out of the sidebar by
setting `include_in_sidebar=False`. This is useful for section homepages that do not belong to a
single app.【F:contrib/admin/core/site.py†L588-L647】

## Template context and assets

Handlers decorated with `register_view()` receive the authenticated `AdminUserDTO` and the request
object. They should return context dictionaries or `TemplateResponse` instances produced via
`admin_site.render()` or `AdminSite.build_template_ctx()`. The demo dashboard shows how to bundle
additional JavaScript or CSS assets with the response payload so the layout can aggregate them on the
client side.【F:apps/demo/views.py†L36-L95】

Because the registration decorator wraps your callable into a `FreeViewPage`, the resulting template
context automatically includes navigation data, branding, breadcrumbs, and permission checks. You do
not need to duplicate layout logic in each view.【F:contrib/admin/core/site.py†L660-L688】

## Creating a view step by step

1. **Place the registrar** – keep view registration close to the owning app (for example,
   `apps/blog/views.py`) so imports stay localized and the app label is easy to reuse.【F:docs/admin/pages.md†L38-L99】
2. **Register cards or assets (optional)** – if your page renders dashboard cards, use
   `AdminSite.register_card()` before registering the view so widgets appear on the landing page.
3. **Declare the view** – decorate an async callable with `admin_site.register_view(...)`, providing
   the path, name, label, and optional icon. Fetch data from services and return a context dict or
   `TemplateResponse`.
4. **Expose a registrar object** – wrap the registration in a class (see `DemoDashboard`) that runs
   at import time. This keeps initialization idempotent and makes it easy to trigger registration from
   your app's `__init__.py` or startup hook.【F:apps/demo/views.py†L12-L134】
5. **Mount the router** – ensure `AdminRouter(admin_site).mount(app)` runs during startup so the
   FastAPI application picks up the newly registered view routes. The tests use this to verify the
   sidebar output.【F:tests/test_views_sidebar.py†L1-L162】

## Inspecting registered views

Use `AdminSite.get_sidebar_views(settings=False)` to inspect the collected metadata grouped by
application. Each entry contains the display name, slug, path, and icon fields ready for rendering in
custom dashboards or analytics views.【F:docs/admin/pages.md†L100-L164】

You can also query the underlying registry through `PageRegistry.view_entries` or
`PageRegistry.virtual_registry` when you need a programmatic snapshot of all registered admin pages.
This is useful for test assertions or for building automated documentation of available views.【F:contrib/admin/core/registry.py†L54-L140】

## Troubleshooting checklist

- **Wrong sidebar highlight** – verify that the view path respects the configured prefix from
  `SettingsKey.VIEWS_PREFIX`; mismatched prefixes prevent the context builder from detecting the
  active entry.【F:contrib/admin/core/site.py†L601-L651】【F:docs/admin/pages.md†L166-L222】
- **Missing navigation entry** – confirm that `include_in_sidebar` is left at `True` and that the
  path contains at least `/views/<app>/<slug>/`. Landing pages without the trailing segments are
  intentionally hidden from the sidebar.【F:contrib/admin/core/site.py†L588-L647】
- **Duplicate registration error** – check for conflicting `(app, slug, settings)` tuples in
  `PageRegistry.view_entries`. Adjust the path or slug to keep them unique.【F:contrib/admin/core/registry.py†L85-L139】

With these conventions in place, admin views offer a consistent way to extend the Cortex panel
without abandoning the shared navigation and theming system.
