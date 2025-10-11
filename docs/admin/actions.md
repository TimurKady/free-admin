# Admin Actions

The admin interface exposes action endpoints that operate on sets of model instances. The underlying logic is handled by the `AdminActionRunner`, which coordinates how an action interacts with the selected objects and the current administrator.

## AdminActionRunner.run

```python
await admin_action_runner.run(app, model, action, scope, params, user, admin_site=None)
```

- **scope** – structure describing the targeted objects. It can contain filters or primary key lists and is used to build a queryset.
- **params** – action-specific options validated against the action's parameter schema.
- **user** – `AdminUserDTO` on whose behalf the action executes.

The runner typically works together with two FastAPI endpoints:

- `actions_preview` – returns how many objects match the provided scope before execution.
- `action_run` – triggers the action itself, delegating heavy tasks to the runner.

Using `actions_preview` followed by `action_run` lets clients confirm the affected object count and then execute the action with the same `scope` and `params` payload.

