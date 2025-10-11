# Admin API

The admin panel exposes a minimal set of helper endpoints for the client UI.
All API paths are defined in `contrib/admin/core/settings` and are injected
into templates as the `window.ADMIN_API` object so that JavaScript and Python
share the same values. See [System Settings](settings.md) for the full list of
configuration keys and defaults:

The examples assume the default prefixes `ADMIN_PREFIX=/panel`,
`API_PREFIX=/api`, and `API_LOOKUP=/lookup`; each value can be customized in
the system settings.

All endpoints expect the `model` parameter to be the model's class name in
lowercase (e.g., `StreamGraph` becomes `streamgraph`).

- `/api/schema` — returns a JSON Schema and start values for the given `app` and
  `model`. When requesting a form for editing, include `mode=edit` and supply the
  object's primary key (`pk`) in the query string. Example:

  ```http
  GET /api/schema?app=streams&model=dummy
  {
    "schema": {"title": "Dummy", "type": "object", ...},
    "startval": {"first_name": ""}
  }
  ```
- `/api/list_filters` — returns available filters for a model's changelist.
  Each entry includes the filter name and its type. Example:

  ```http
  GET /api/list_filters?app=app&model=dummy
  {"filters": [{"name": "active", "kind": "boolean"}]}
  ```
- `/api/lookup/{app}/{model}/{field}` — provides remote lookup data for
  relational fields. Filtering is handled by the administrator via
  `get_choices(field_name)`, and the endpoint accepts no custom query
  parameters.
- `/api/action/{app}.{model}/list` — returns metadata about available
  administrative actions.
- `/api/action/{app}.{model}/preview` — returns the number of objects
  affected by an action scope.
- `/api/action/{app}.{model}/token` — signs an action scope and returns a
  `scope_token` for reuse.
- `/api/action/{app}.{model}/{action}` — executes an administrative action.
  If the affected count exceeds the `ACTION_BATCH_SIZE` setting,
  the response is `{"ok": true, "background": true}` and the task runs
  asynchronously.
- `/<parent>/<pk>/_inlines` — retrieves specifications for inline admins
  attached to a parent object. Each entry includes `label`, `app`, `model`,
  `parent_fk`, `can_add`, `can_delete`, `columns` and `columns_meta`. Requires
  change permission on the parent model. Example:

  ```http
  GET /books/1/_inlines
  [
    {
      "label": "Chapters",
      "app": "library",
      "model": "chapter",
      "parent_fk": "book",
      "can_add": true,
      "can_delete": true,
      "columns": ["title"],
      "columns_meta": [
        {"key": "title", "label": "Title", "type": "string"}
      ]
    }
  ]
  ```

Use `scope_token` when an action targets a large set of objects or contains a
complex query. Calling `/api/action/{app}.{model}/token` signs the scope once so
that `/api/action/{app}.{model}/{action}` can be invoked with just the returned
`scope_token` instead of resending the entire scope payload.

To request filtered results from a changelist endpoint, prefix query parameters
with `filter.` followed by the field name and operation. For example, to filter
books by author name:

```http
GET /admin/books/_list?filter.author.name.eq=Alpha
```

Each handler relies on FastAPI dependencies for authorization and expects the
current user to be provided by `require_model_permission(PermAction.view)`:

```python
user: AdminUserDTO = Depends(require_model_permission(PermAction.view))
```

There are no manual permission checks inside the handlers. Unknown admin models
are resolved through `AdminSite.find_admin_or_404` which returns HTTP 404.
