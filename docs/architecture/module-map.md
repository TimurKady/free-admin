# Карта модулей FreeAdmin

## 1. Текущее состояние модулей

Эти сведения отражают файловую и логическую структуру каталога `freeadmin/` в текущем состоянии репозитория. Основное внимание уделено узлам, участвующим в инициализации административного ядра, интеграции с FastAPI и обслуживании пользовательского интерфейса.

### 1.1 Ключевые модули и прямые зависимости

| Путь | Назначение | Прямые зависимости первого порядка |
| --- | --- | --- |
| `freeadmin/core/application/factory.py` | Фабрика FastAPI-приложений, связывает настройки, ORM и роутеры | `freeadmin.core.boot.BootManager`, `freeadmin.core.data.orm.ORMConfig/ORMLifecycle`, `freeadmin.core.network.router.AdminRouter`, `freeadmin.core.runtime.hub.admin_site` |
| `freeadmin/core/boot/manager.py` | Управляет адаптерами, регистрацией моделей и запуском хаба | Реестр адаптеров (`freeadmin.contrib.adapters`), системные настройки (`freeadmin.core.configuration.conf`), посредник `freeadmin.core.runtime.middleware.AdminGuardMiddleware`, хаб `freeadmin.core.runtime.hub` |
| `freeadmin/core/configuration/conf.py` | Хранилище конфигурации и наблюдатель за изменениями окружения | `os`, `pathlib`, синхронизация через `threading.RLock` |
| `freeadmin/core/runtime/hub.py` | Центральный хаб админки: управляет сайтом, автодискавери и роутерами | Настройки (`freeadmin.core.configuration.conf`), `freeadmin.core.interface.site.AdminSite`, `freeadmin.core.interface.discovery.DiscoveryService`, `freeadmin.core.network.router.AdminRouter`, `freeadmin.core.boot.admin` |
| `freeadmin/core/interface/site.py` | Реализация админ-сайта: регистрация моделей/страниц, меню, экспорт | Сервисы интерфейса (`freeadmin.core.interface.*`), адаптеры, CRUD, API карточек, поставщик шаблонов, проверки миграций |
| `freeadmin/core/network/router/base.py` | Базовые вспомогательные классы для монтирования админ-маршрутов | `fastapi.FastAPI`, `freeadmin.core.interface.templates.TemplateService`, `freeadmin.core.interface.site.AdminSite` |
| `freeadmin/core/network/router/aggregator.py` | Координатор создания и подключения админ- и публичных роутеров | `freeadmin.core.network.router.base.RouterFoundation`, `fastapi.APIRouter`, `freeadmin.core.interface.site.AdminSite`, `freeadmin.core.interface.templates.TemplateService` |
| `freeadmin/core/runtime/provider.py` | Управление шаблонами, статикой и медиа | `fastapi`, `starlette.staticfiles.StaticFiles`, `freeadmin.core.configuration.conf.FreeAdminSettings`, `freeadmin.core.interface.settings.system_config` |
| `freeadmin/core/runtime/middleware.py` | Middleware охраны админки (суперпользователь, сессия) | `starlette` middleware, `freeadmin.core.configuration.conf`, `freeadmin.core.interface.settings`, `freeadmin.core.boot.admin` |
| `freeadmin/contrib/crud/operations.py` | Построитель CRUD-роутов и файлового обмена | `fastapi`, сервисы `freeadmin.core.interface`, `freeadmin.core.configuration.conf`, `freeadmin.core.interface.settings`, `freeadmin.core.interface.services` |
| `freeadmin/api/base.py` | Обёртка системного API админки | `fastapi.APIRouter`, `freeadmin.contrib.adapters.BaseAdapter`, системные API `freeadmin.contrib.apps.system.api.views`, сервисы `freeadmin.core.interface` |
| `freeadmin/core/data/orm/config.py` | Конфигурация ORM и жизненный цикл Tortoise | `tortoise` ORM, реестр адаптеров, классификатор ошибок миграций (`freeadmin.utils.migration_errors`) |

## 2. Уровни важности

- **Ядро**: `freeadmin/core/` (подпакеты `application`, `boot`, `configuration`, `data`, `interface`, `network`, `runtime`), а также `freeadmin/contrib/adapters/` и вспомогательные модели. Эти элементы отвечают за конфигурацию, регистрацию ресурсов, связь с ORM и глобальные сервисы.
- **Оболочки**: `freeadmin/api/`, совместимые фасады `freeadmin/router/`, `freeadmin/crud.py`, `freeadmin/middleware.py`, `freeadmin/pages/`, `freeadmin/widgets/`, `freeadmin/templates/`, `freeadmin/static/`, `freeadmin/runner.py`, `freeadmin/cli.py`. Модули обеспечивают HTTP-интерфейсы, UI и вспомогательные сценарии.
- **Утилиты**: `freeadmin/utils/`, `freeadmin/schema/`, `freeadmin/tests/`, `freeadmin/provider.py`, `freeadmin/meta.py`. Служебные компоненты и расширяемые помощники.

## 3. Структура ядра после реорганизации

### 3.1 Логика группировки

* **`core/application/`** — фабрики и протоколы, которые собирают FastAPI‑приложения с подключённой админкой.
* **`core/boot/`** — менеджер запуска, координирующий адаптеры, системные приложения и подключение middleware.
* **`core/configuration/`** — настройки и менеджер конфигурации, наблюдающий за изменениями окружения.
* **`core/data/`** — интеграция с ORM и вспомогательные модели данных.
* **`core/interface/`** — админские дескрипторы, сервисы, шаблонные помощники и REST-интерфейсы верхнего уровня.
* **`core/network/`** — роутеры и агрегаторы, отвечающие за монтирование HTTP-маршрутов админки.
* **`core/runtime/`** — хаб, middleware, поставщик шаблонов и другой код, работающий во время исполнения.

Внешние расширения и интеграции лежат в `freeadmin/contrib/`, включая адаптеры и CRUD-утилиты. В актуальной структуре верхнеуровневые фасады удалены: проекты подключают компоненты напрямую из подпакетов `core/` и `contrib/`.

### 3.2 Основные публичные модули

| Путь | Назначение |
| --- | --- |
| `freeadmin/core/application` | Фабрики FastAPI-приложений. |
| `freeadmin/core/boot` | Менеджер запуска и адаптеры. |
| `freeadmin/core/runtime/hub.py` | Центральный хаб и автодискавери. |
| `freeadmin/core/configuration/conf.py` | Настройки и менеджер конфигурации. |
| `freeadmin/core/data/orm` | Конфигурация ORM и жизненный цикл. |
| `freeadmin/core/network/router` | Агрегаторы и вспомогательные роутеры. |
| `freeadmin/core/runtime/provider.py` | Поставщик шаблонов и статики. |
| `freeadmin/core/runtime/middleware.py` | AdminGuard и связанные middleware. |
| `freeadmin/contrib/crud/operations.py` | Построитель CRUD-маршрутов. |
