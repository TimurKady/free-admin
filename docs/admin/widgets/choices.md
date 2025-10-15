# ChoicesWidget

`ChoicesWidget` wraps JSONEditor's [Choices](https://github.com/json-editor/json-editor#choices-select-editor) integration to provide rich single- or multi-select controls powered by [Choices.js](https://github.com/Choices-js/Choices). It renders an array input only when the field uses a many-to-many relation; otherwise a single select is used.

The admin bundles `/static/widgets/choices.js`, which mirrors the Select2 helper and waits for both JSONEditor and the Choices.js library to become available. When either dependency fails to load (for example, due to CDN issues), the script surfaces a prominent warning banner so administrators immediately understand why the enhanced dropdown is unavailable.

```json
{
  "type": "array",
  "format": "checkbox",
  "items": {
    "type": "string",
    "enum": ["py", "js"],
    "options": {"enum_titles": ["Python", "JavaScript"]}
  },
  "options": {"placeholder": "Select tags…"}
}
```

## FastAPI example

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field
from freeadmin.core.interface.models import ModelAdmin
from freeadmin.widgets import ChoicesWidget
from freeadmin.core.boot import admin


class Post(BaseModel):
    tags: list[str] = Field(
        default_factory=list,
        json_schema_extra={
            "relation": {"kind": "m2m", "target": "app.Tag"},
            "choices_map": {"py": "Python", "js": "JavaScript", "go": "Go"},
            "placeholder": "Select tags…",
            "choices_options": {"allowSearch": True, "removeItemButton": True},
        },
    )


class PostAdmin(ModelAdmin):
    class Meta:
        model = Post
        widgets = {"tags": ChoicesWidget()}


app = FastAPI()
admin.init(app, packages=["apps"])
```

The `tags` field declares a many-to-many relation to `Tag`, so the widget is rendered as a multi-select control. `choices_map` defines the available values and their labels. The optional `placeholder` sets the empty item label, and any extra settings for Choices.js can be supplied in `choices_options`, which is merged with the default `{"removeItemButton": True}`.
