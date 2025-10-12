# RBAC Guide

This document explains how to grant permissions and protect CRUD endpoints in the
admin panel using the new role-based access control (RBAC) system.

## 1. Granting Permissions

Permissions are flat and consist of an action (`view`, `add`, `change`,
`delete`) optionally tied to a model via its content type (`content_type_id`).
When a user accesses a resource the system checks permissions in the following
order:

1. **Superuser** – automatically passes all checks.
2. **User permissions** – explicit permissions assigned directly to the user.
3. **Group permissions** – permissions inherited from groups the user belongs
to.

### Prepare Content Types

Before issuing model permissions ensure that a `ContentType` record exists for
the model:

1. Register all models with `AdminSite`.
2. Call `admin_site.finalize()` after registration. This populates the
   `admin_content_type` table and stores `ct_id` for each `(app, model)` pair.

### Virtual Content Types

Cards and standalone views are exposed as **virtual** content types. Their
dotted names follow the `app.kind.slug` convention, for example
`reports.cards.alpha` or `reports.views.traffic`. During
`admin_site.finalize()` the admin automatically creates rows for these entries
and keeps them in sync on every run.

The `admin_content_type` columns store:

* `app_label` – normalized app slug (e.g. `reports`).
* `model` – synthetic identifier such as `cards.alpha` or `views.dashboard`.
* `dotted` – the canonical dotted name used by permissions.

Use the helper script to backfill virtual content types for existing
deployments:

```bash
python -m contrib.utils.scripts.backfill_virtuals
```

To inspect or update permissions for these entries from the command line:

```bash
# List available virtual content types
python -m contrib.utils.scripts.permissions_cli list-virtual

# Grant a card permission to a user
python -m contrib.utils.scripts.permissions_cli grant --user alice --dotted reports.cards.alpha --action view

# Revoke a view permission from a group
python -m contrib.utils.scripts.permissions_cli revoke --group viewers --dotted reports.views.dashboard --action view
```

The commands operate atomically and provide clear messages on success or
failure.

Without running `finalize()` any model‑specific permission assignment is
meaningless because the corresponding content type entries do not exist.

### Assign Permissions to Users

To grant rights directly to a user provide the `user_id`, `ct_id` (or `None`
for global permissions) and the desired action:

```python
# Model‑specific permission
a = AdminUserPermission.create(
    user_id=..., content_type_id=..., action="change"
)

# Global permission
a = AdminUserPermission.create(
    user_id=..., content_type=None, action="view"
)
```

### Assign Permissions via Groups

Groups allow managing permissions for multiple users:

```python
g = AdminGroup.create(name="Editors")
g.users.add(user)

# Model permission
AdminGroupPermission.create(
    group_id=g.id, content_type_id=..., action="delete"
)

# Global permission
AdminGroupPermission.create(
    group_id=g.id, content_type=None, action="view"
)
```

Use groups for mass assignment and maintenance.

### Recommended Policy

* Distribute baseline `view` rights through groups.
* Issue `add`, `change`, and `delete` only via dedicated editor/operator groups.
* Grant direct user permissions only for rare exceptions.

### Find a `ct_id`

```python
ct_id = admin_site.get_ct_id(app="streams", model="stream")
```

The function returns `None` if the model is unregistered or `finalize()` was not
called.

### Verify Permission Assignment

For a quick smoke test:

1. User is active, not a superuser and has `staff=True`.
2. Check for the expected `(ct_id, action)` pair in
   `admin_user_permissions`. If not found, look in
   `admin_group_permissions` through the user's groups.

If a matching record exists in either table the user has access.

## 2. Securing CRUD Endpoints

Each CRUD route maps to exactly one permission action. A dependency reads the
`{app, model}` from the path, resolves the `ct_id` via
`AdminSite.get_ct_id()` and enforces the required permission.

The leading `/panel/orm/` segment comes from configuration: `panel` is the
`ADMIN_PREFIX` and `orm` is `PAGE_TYPE_ORM`, both defined in project
settings.

### Action Mapping

| HTTP route                                         | Action |
| -------------------------------------------------- | ------ |
| `GET /panel/orm/{app}/{model}/_list`               | view   |
| `GET /panel/orm/{app}/{model}/{id}`                | view   |
| `POST /panel/orm/{app}/{model}/`                   | add    |
| `PUT/PATCH /panel/orm/{app}/{model}/{id}`          | change |
| `DELETE /panel/orm/{app}/{model}/{id}`             | delete |

### Applying the Dependency

**Per Route** – Add the dependency manually:

```python
@router.get(..., dependencies=[Depends(require_model_permission(PermAction.view))])
```

**Centralized** – When CRUD routes are generated automatically (e.g. in
`contrib/admin/core/site.py`), maintain a small table mapping endpoint types to
`PermAction` values and inject the `Depends(...)` call during registration. This
ensures uniform protection across all models.

### Special Endpoints

Non‑CRUD actions such as `export`, `bulk_delete` or `autocomplete` should be
mapped to the closest existing action (`view` for `export`, `delete` for
`bulk_delete`, etc.). Additional actions can be added to `PermAction` if needed.

### Global Pages

Pages like **Settings** use `require_global_permission()` instead of model
checks:

```python
require_global_permission(PermAction.view)    # read
require_global_permission(PermAction.change)  # write
```

### Startup Order

During application startup register models with `AdminSite`, then call
`finalize()`. Only after this step will dependencies like
`require_model_permission` see valid `ct_id` values.

### Coupled `view` for Higher Rights

While `change` and `delete` can technically exist without `view`, in practice
issue `view` automatically whenever granting `change` or `delete` permissions.
This policy is enforced during permission assignment, not in the permission
check itself.

### Superuser Shortcut

Superusers bypass all permission checks. This acts as a universal escape hatch
for administrators.

---

This RBAC workflow keeps permission management straightforward and avoids
complex synchronization or caching. The system remains transparent, predictable
and easy to maintain.

