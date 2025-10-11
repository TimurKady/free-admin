# Admin Boot Process

Initialize the admin application through the ``admin`` boot manager.
It wires configuration startup hooks, registers middleware, registers
built-in pages and mounts the admin site onto the ASGI application.

## Quick start

```python
from fastapi import FastAPI
from freeadmin.boot import admin
from my_project.adapters import MyAdapter

app = FastAPI()
admin.init(app, adapter=MyAdapter(), packages=["apps", "contrib", "core"])

```

## Adapter selection

Provide the database backend via the ``adapter`` keyword. Supply any object
implementing the adapter protocol, and ``BootManager`` will resolve it at
startup and apply the required configuration.

## BootManager responsibilities

``BootManager`` consolidates tasks that previously required manual setup:

- registering middleware and configuration hooks
- loading page definitions from the supplied packages
- mounting the admin site on the ASGI application

These steps replace any manual ``AdminRouter`` mounting.

## Middleware

``AdminGuardMiddleware`` protects the admin interface. It redirects unauthenticated users to the login page and forces initial setup when no superuser exists. Configuration values are read from ``SystemConfig`` and cached for efficiency:

- ``ADMIN_PREFIX`` – base URL prefix for the admin site.
- ``LOGIN_PATH`` – relative path to the login view.
- ``LOGOUT_PATH`` – relative path to the logout view.
- ``SETUP_PATH`` – path used for the initial superuser creation.
- ``STATIC_PATH`` – location of static assets served by the admin.
- ``SESSION_KEY`` – session key storing the authenticated user identifier.
- ``SESSION_COOKIE`` – session cookie name.

Example FastAPI integration:

```python
from fastapi import FastAPI
from freeadmin.middleware import AdminGuardMiddleware

app = FastAPI()
app.add_middleware(AdminGuardMiddleware)
```

## CSRF Protection

Login and setup forms embed a CSRF token stored in the session. Each POST
handler verifies the ``csrf_token`` field before processing the request.

For details on manual mounting and autodiscovery see [Hub and Router](hub-router.md).


# The End

