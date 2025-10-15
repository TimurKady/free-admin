# Front-end assets

This note describes how static assets are loaded in the admin panel.

## Base template

`contrib/admin/templates/base.html` loads the global libraries available on all
admin pages: Bootstrap 5 styles, Bootstrap Icons, and the Bootstrap bundle. It
also injects API endpoints into `window.ADMIN_API` and loads a small
`sidebar.js` helper that activates the navigation sidebar.

## Form assets

JSONEditor and any widget scripts are included statically by the template. The
form template also loads `admin-form.js`, which fetches the schema, initializes
JSONEditor, and submits changes using the Fetch API without relying on
additional libraries.

Widget scripts such as `/static/widgets/barcode-editor.js` only register custom
editors after their dependencies (`JSONEditor` and `JsBarcode`) are available.
`form.html` waits for `JSONEditorInitializer.ready` before instantiating the
form editor, ensuring the libraries loaded in `Meta.js` are ready and that
custom editors are registered before any `JSONEditor` instance is created.

## JSON Editor lifecycle events

`admin-form.js` dispatches a trio of DOM `CustomEvent` notifications so widget
bundles can respond to the JSON Editor lifecycle without importing
`admin-form.js` directly:

- `admin:jsoneditor:schema` — fired after the schema is fetched and presets are
  applied. The event `detail` contains `{schema}` and allows widgets to mutate
  or annotate the schema before the editor is created.
- `admin:jsoneditor:created` — emitted immediately after `new JSONEditor(...)`
  returns with `{editor}` in the payload. Widgets can use this to register
  `editor.on(...)` listeners for deferred setup.
- `admin:jsoneditor:ready` — triggered once the editor's internal `ready` hook
  fires (or immediately when the instance lacks a `ready` event). Consumers
  receive `{editor}` and can safely interact with the rendered form controls.

The `FilePathWidget` uploader listens to these events to register upload
callbacks once `JSONEditor` is available and to refresh any existing download
links after editors finish rendering.

## Select2 availability

`admin-form.js` integrates Select2 when present. If the library fails to load,
the script logs a warning advising developers to verify CDN availability and
network connectivity. A temporary banner is also shown to highlight the missing
dependency during development.

## Favicon

Save the `favicon.ico` file in `contrib/admin/static/`. `TemplateProvider.mount_favicon`
mounts this file at `/favicon.ico` when the router aggregator attaches the
admin interface, ensuring it is automatically available to browsers.

<!-- # The End -->

