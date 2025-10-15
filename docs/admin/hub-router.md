# Hub and Router

`AdminHub` manages the admin site's discovery and mounting logic.

## Autodiscovery

`AdminHub.autodiscover` walks the given packages and imports modules named `admin` or containing the `.admin` segment. Importing these modules registers admin pages so that the site can expose them later.

```python
from freeadmin.hub import hub

hub.autodiscover(["apps.blog", "apps.shop"])
```

## init_app shortcut

`AdminHub.init_app` combines autodiscovery with mounting the site on a FastAPI application:

```python
from fastapi import FastAPI
from freeadmin.hub import hub

app = FastAPI()
hub.init_app(app, packages=["apps.blog", "apps.shop"])
```

The call above imports all admin modules from the listed packages and mounts the admin site on the application.

## Mounting and assets

`AdminRouter.mount` delegates to the underlying `RouterAggregator`. The aggregator attaches the admin router, stores the site on `app.state`, and delegates template and static handling to `TemplateProvider` while caching those mounts so repeated calls stay idempotent.

`TemplateProvider` builds the `Jinja2Templates` environment and mounts static files under the admin's prefix so that templates and assets are available without additional configuration.

# The End

