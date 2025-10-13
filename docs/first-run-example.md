# First Run Example

The repository ships with a fully wired demonstration project that shows how
FreeAdmin glues together configuration, data models, live cards, and custom
views. This page walks through the pieces you get out of the box and explains
how to launch them locally for your own exploration.

## Project snapshot

The example project lives in the top-level `example/` package. Its entry point is
`ExampleApplication`, a small object that assembles the FastAPI application and
boots the admin site.

```python
from example import ExampleApplication

application = ExampleApplication()
app = application.configure()
```

`ExampleApplication` wires three responsibilities:

* `ExampleSettings` (`example/config/settings.py`) keeps track of project
  metadata, the admin path (`/panel`), and the list of installed apps. Its
  `describe()` helper returns a concise summary that is useful for debugging
  configuration during development.
* `ExampleORMConfig` (`example/config/orm.py`) declares which adapter to use
  (`tortoise` by default) together with the database DSN. The configuration is
  intentionally simple and points to an in-memory SQLite database so you can
  explore the admin without provisioning external infrastructure.
* The `BootManager` binds the FastAPI app and discovers admin resources in the
  `example.apps` and `example.pages` packages. You can register additional
  packages before calling `configure()` if you want to experiment with your own
  resources:

  ```python
  application.register_packages([
      "example.apps",
      "example.pages",
      "myproject.admin",  # add your own package
  ])
  app = application.configure()
  ```

## Launching the demo

1. Install the project together with the demo extras. From the repository root:

   ```bash
   pip install -e .[demo]
   ```

   The editable install ensures the example package and static files are on the
   Python path while you iterate.

2. Start the FastAPI server with Uvicorn:

   ```bash
   uvicorn example_app:app --factory
   ```

   Create a minimal `example_app.py` next to the command if you want to keep the
   shell clean:

   ```python
   from fastapi import FastAPI

   from example import ExampleApplication


   def app() -> FastAPI:
       application = ExampleApplication()
       return application.configure()
   ```

   The admin interface will be available at `http://127.0.0.1:8000/panel` once
   the server is running. On the first visit you will be redirected to the
   built-in setup screen where you can create the initial superuser. You can
   also create it ahead of time from the command line:

   ```bash
   freeadmin create-superuser --username admin --email admin@example.com
   ```

## Exploring the admin

After logging in you are greeted by the **Demo** dashboard, a compact showcase of
several FreeAdmin features.


[*Demo dashboard*](images/scr-1.jpg)

### Demo application

The demo application is defined in `example/apps/demo/`. The `DemoConfig`
(AppConfig subclass) registers two moving parts during the application startup:

```python
class DemoConfig(AppConfig):
    app_label = "demo"
    name = "example.apps.demo"

    async def startup(self) -> None:
        admin_site.cards.register_publisher(self.publisher)
```

*The admin card.* `DemoTemperatureCard` registers an interactive card with the
key `thermo1`. The card uses the `cards/thermo.html` template bundled with the
package and subscribes to the `sensor:temp` channel. The companion
`TemperaturePublisher` (`example/apps/demo/service.py`) is a background service
that emits random temperature readings every second. Because `DemoConfig`
registers the publisher at startup, the card begins streaming data as soon as the
admin boots.

*The custom view.* `DemoHelloView` demonstrates how to expose an arbitrary admin
page. It lives at `/demo/hello`, renders a “Hello world!” message with the count
of registered users, and attaches a small JavaScript snippet from
`example/static/js/demo-hello.js`. The view showcases the `register_view`
decorator and how to request extra assets for the page.

### Working with data

`example/apps/demo/models.py` declares a single `DemoNote` model backed by
Tortoise ORM. The corresponding `DemoNoteAdmin` class in
`example/apps/demo/admin.py` makes the model editable through the admin interface
with search, list display, and detail forms already configured. Because the
example uses SQLite in memory, the database resets when you restart the server;
this keeps experiments reproducible.

### Standalone welcome page

`example/pages/home.py` shows how to register additional views that are not tied
to a specific application. The `ExampleWelcomePage` registers a friendly welcome
screen under `/example/welcome` with custom iconography. The implementation uses
`admin_site.build_template_ctx()` to reuse FreeAdmin’s standard layout while
injecting its own message.

## Next steps

Once you are comfortable with the example project you can start replacing pieces
with your own domain logic: swap out the in-memory database for a persistent DSN,
add more models to `INSTALLED_APPS`, or create additional cards and views. The
objects in the example package are intentionally small, so you can use them as
copy-paste-friendly templates when bootstrapping a real project.
