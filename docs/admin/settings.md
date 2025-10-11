# System Settings

The admin panel reads configuration values via the `SystemConfig` helper. Each option is identified by a `SettingsKey` and persisted in the `SystemSetting` table.

## Working with `SystemConfig`

```python
from freeadmin.core.settings.config import system_config, SettingsKey

# insert any missing defaults
await system_config.ensure_seed()

# read a value
per_page = await system_config.get(SettingsKey.DEFAULT_PER_PAGE)

# update a value
await system_config.set(SettingsKey.DEFAULT_PER_PAGE, 50)

# refresh the in-memory cache
await system_config.reload()
```

## Available keys

| Key | Description | Default | Type |
| --- | --- | --- | --- |
| `DEFAULT_ADMIN_TITLE` | Admin panel title | `FastAPI FreeAdmin` | `string` |
| `DASHBOARD_PAGE_TITLE` | Dashboard page title | `Dashboard` | `string` |
| `VIEWS_PAGE_TITLE` | Views section title | `Views` | `string` |
| `ORM_PAGE_TITLE` | ORM section title | `ORM` | `string` |
| `SETTINGS_PAGE_TITLE` | Settings section title | `Settings` | `string` |
| `BRAND_ICON` | Brand icon path | `icon-36x36.png` | `string` |
| `VIEWS_PAGE_ICON` | Views icon (Bootstrap 5 class) | `bi-eye` | `string` |
| `ORM_PAGE_ICON` | ORM icon (Bootstrap 5 class) | `bi-diagram-3` | `string` |
| `SETTINGS_PAGE_ICON` | Settings icon (Bootstrap 5 class) | `bi-gear` | `string` |
| `PASSWORD_ALGO` | Password hashing algorithm | `pbkdf2_sha256` | `string` |
| `PASSWORD_ITERATIONS` | Password hashing iterations | `390000` | `int` |
| `PAGE_TYPE_ORM` | Page type: ORM | `orm` | `string` |
| `PAGE_TYPE_VIEW` | Page type: View | `view` | `string` |
| `PAGE_TYPE_SETTINGS` | Page type: Settings | `settings` | `string` |
| `DEFAULT_PER_PAGE` | Default page size | `20` | `int` |
| `MAX_PER_PAGE` | Max page size | `100` | `int` |
| `ACTION_BATCH_SIZE` | Batch size for admin actions | `100` | `int` |
| `ADMIN_PREFIX` | Admin path prefix used to build final admin URLs; other paths like `LOGIN_PATH` and `LOGOUT_PATH` are appended to this prefix | `/panel` | `string` |
| `API_PREFIX` | API prefix | `/api` | `string` |
| `API_SCHEMA` | Schema endpoint | `/schema` | `string` |
| `API_LIST_FILTERS` | List filters endpoint | `/list_filters` | `string` |
| `API_LOOKUP` | Lookup endpoint | `/lookup` | `string` |
| `LOGIN_PATH` | Login path appended to `ADMIN_PREFIX` to form the full login URL | `/login` | `string` |
| `LOGOUT_PATH` | Logout path appended to `ADMIN_PREFIX` to form the full logout URL | `/logout` | `string` |
| `SETUP_PATH` | Setup path | `/setup` | `string` |
| `SESSION_COOKIE` | Admin session cookie name | `session` | `string` |
| `SESSION_KEY` | Admin session cookie key | `admin_user_id` | `string` |
| `ORM_PREFIX` | ORM section prefix | `/orm` | `string` |
| `SETTINGS_PREFIX` | Settings section prefix | `/settings` | `string` |
| `VIEWS_PREFIX` | Views section prefix | `/views` | `string` |
| `STATIC_PATH` | Static files path | `/static` | `string` |
| `STATIC_URL_SEGMENT` | Static URL segment | `/static` | `string` |
| `STATIC_ROUTE_NAME` | Static route name | `admin-static` | `string` |
| `MEDIA_ROOT` | Directory for uploaded files | `media` | `string` |
| `MEDIA_URL` | URL prefix for uploaded files | `/media` | `string` |
| `ROBOTS_DIRECTIVES` | robots.txt directives returned by `/robots.txt` | `User-agent: *\nDisallow: /\n` | `string` |
| `CARD_EVENTS_TOKEN_TTL` | Lifetime of signed tokens for card event streams (seconds) | `300` | `int` |

Invoking `/logout` without the `ADMIN_PREFIX` will return a 404.

All path prefixes must align. The combination of `ADMIN_PREFIX` and
`API_PREFIX` must match the leading part of `API_LOOKUP`; otherwise, URL
construction for widgets such as `Select2Widget` will fail.

## Storage

All values are stored in the `SystemSetting` model with a simple type marker. Supported types include `string`, `int` and `bool`.

# The End

