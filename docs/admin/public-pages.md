# Public pages

FreeAdmin can expose public FastAPI pages alongside the administrative interface. The
`ExtendedRouterAggregator` coordinates both the `/admin` routes and additional routers
mounted in the root URL space so that projects keep a single integration point.

## Architecture overview

``RouterAggregator`` builds the administrative router, mounts static files, and caches
the resulting `APIRouter`. `ExtendedRouterAggregator` inherits from it and introduces:

- `add_admin_router()` – register extra admin routers (mounted under the admin prefix);
- `add_additional_router()` – register public routers without any prefix;
- `get_routers()` – retrieve all routers honouring the desired order;
- `router` – an aggregated `APIRouter` that can be included directly.

Pass `public_first=False` when instantiating the class to keep admin routes ahead of
public ones.

## Example: registering the welcome page

Register a public page in `example/pages/welcome_page.py`:

```python
from fastapi import Request

from freeadmin.hub import admin_site


@admin_site.register_public_view(
    path="/",
    name="Welcome",
    template="welcome.html",
)
async def public_welcome(request: Request, user=None) -> dict[str, object]:
    return {"subtitle": "Rendered outside the admin", "user": user}
```

Handlers decorated with `register_public_view()` return a mapping used as template
context. The page manager injects the request, anonymous user, and page title before
rendering the template through :class:`PageTemplateResponder`.

Place a template at `example/templates/welcome.html`. It can extend the
administrative layout while remaining visually independent:

```jinja
{% extends "layout/base.html" %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
<div class="fa-public-welcome">
    <section class="fa-public-welcome__hero">
        <h1 class="fa-public-welcome__title">{{ title }}</h1>
        <p class="fa-public-welcome__subtitle">This page lives outside the admin panel.</p>
    </section>
    <section class="fa-public-welcome__body">
        <p>
            Customize this template freely. It shares the same rendering engine as the
            administration area but does not depend on its styling.
        </p>
    </section>
</div>
{% endblock %}
```

## Registering routers

```python
from fastapi import FastAPI

from freeadmin.core.interface.site import admin_site
from freeadmin.core.network.router import ExtendedRouterAggregator

app = FastAPI()
aggregator = ExtendedRouterAggregator(site=admin_site)
aggregator.add_admin_router(aggregator.get_admin_router())
aggregator.mount(app)
```

`mount()` ensures the admin site is cached, registers the favicon, static files, and
exposes registered public pages without adding a prefix. Additional routers can still
be registered via :meth:`ExtendedRouterAggregator.add_additional_router` when needed.

## Adding new public pages

1. Create a module under your project's pages package (for example,
   `example/pages/`).
2. Decorate an async handler with :meth:`AdminSite.register_public_view` and return a
   mapping representing the template context.
3. Provide a template in your project's template directory.
4. Call :meth:`ExtendedRouterAggregator.mount` or include
   :attr:`ExtendedRouterAggregator.router` in your FastAPI app.

## Integrating with an existing ``main.py``

```python
from fastapi import FastAPI

from freeadmin.core.interface.site import admin_site
from freeadmin.core.network.router import ExtendedRouterAggregator

app = FastAPI()

aggregator = ExtendedRouterAggregator(site=admin_site, public_first=True)
aggregator.add_admin_router(aggregator.get_admin_router())
app.include_router(aggregator.router)
```

`aggregator.router` combines all registered routers. Calling `mount()` remains
available when you need FreeAdmin to mount static assets for you automatically.
