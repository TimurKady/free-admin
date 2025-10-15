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

Create a public page router in `freeadmin/pages/example_welcome_page.py`:

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from freeadmin.templates import render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    context = {"request": request, "title": "Welcome", "user": None}
    return render_template("welcome.html", context)
```

Place a template at `freeadmin/templates/pages/welcome.html`:

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

from freeadmin.core.site import admin_site
from freeadmin.pages.example_welcome_page import router as welcome_router
from freeadmin.router import ExtendedRouterAggregator

app = FastAPI()
aggregator = ExtendedRouterAggregator(site=admin_site)
aggregator.add_admin_router(aggregator.get_admin_router())
aggregator.add_additional_router(welcome_router)
aggregator.mount(app)
```

`mount()` ensures the admin site is cached, registers the favicon, static files, and
exposes each public router without adding a prefix.

## Adding new public pages

1. Create a module under `freeadmin/pages/` exporting an `APIRouter`.
2. Render templates via `freeadmin.templates.render_template()` to share the admin
   template engine and settings.
3. Register the router with `ExtendedRouterAggregator.add_additional_router()`.
4. Call `aggregator.mount(app)` or include `aggregator.router` in your FastAPI app.

## Integrating with an existing ``main.py``

```python
from fastapi import FastAPI

from freeadmin.core.site import admin_site
from freeadmin.pages.example_welcome_page import router as welcome_router
from freeadmin.router import ExtendedRouterAggregator

app = FastAPI()

aggregator = ExtendedRouterAggregator(site=admin_site, public_first=True)
aggregator.add_admin_router(aggregator.get_admin_router())
aggregator.add_additional_router(welcome_router)
app.include_router(aggregator.router)
```

`aggregator.router` combines all registered routers. Calling `mount()` remains
available when you need FreeAdmin to mount static assets for you automatically.
