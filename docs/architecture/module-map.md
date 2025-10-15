# Карта модулей FreeAdmin

## 1. Текущее состояние модулей

Эти сведения отражают файловую и логическую структуру каталога `freeadmin/` в текущем состоянии репозитория. Основное внимание уделено узлам, участвующим в инициализации административного ядра, интеграции с FastAPI и обслуживании пользовательского интерфейса.

### 1.1 Ключевые модули и прямые зависимости

| Путь | Назначение | Прямые зависимости первого порядка |
| --- | --- | --- |
| `freeadmin/application/factory.py` | Фабрика FastAPI-приложений, связывает настройки, ORM и роутеры | `freeadmin.boot.BootManager`, `freeadmin.orm.ORMConfig/ORMLifecycle`, `freeadmin.router.AdminRouter`, `freeadmin.hub.admin_site` |
| `freeadmin/boot/manager.py` | Управляет адаптерами, регистрацией моделей и запуском хаба | Реестр адаптеров (`freeadmin.contrib.adapters`), системные настройки (`freeadmin.conf`, `freeadmin.core.settings`), посредник `AdminGuardMiddleware`, хаб `freeadmin.hub` |
| `freeadmin/conf.py` | Хранилище конфигурации и наблюдатель за изменениями окружения | `os`, `pathlib`, синхронизация через `threading.RLock` |
| `freeadmin/hub.py` | Центральный хаб админки: управляет сайтом, автодискавери и роутерами | Настройки (`freeadmin.conf`), `freeadmin.core.site.AdminSite`, `freeadmin.core.discovery.DiscoveryService`, `freeadmin.router.AdminRouter`, `freeadmin.boot.admin` |
| `freeadmin/core/site.py` | Реализация админ-сайта: регистрация моделей/страниц, меню, экспорт | Сервисы ядра (`freeadmin.core.*`), адаптеры, CRUD, API карточек, поставщик шаблонов, проверки миграций |
| `freeadmin/router/base.py` | Базовые вспомогательные классы для монтирования админ-маршрутов | `fastapi.FastAPI`, `freeadmin.core.templates.TemplateService`, `freeadmin.core.site.AdminSite` |
| `freeadmin/router/aggregator.py` | Координатор создания и подключения админ- и публичных роутеров | `freeadmin.router.base.RouterFoundation`, `fastapi.APIRouter`, `freeadmin.core.site.AdminSite`, `freeadmin.core.templates.TemplateService` |
| `freeadmin/provider.py` | Управление шаблонами, статикой и медиа | `fastapi`, `starlette.staticfiles.StaticFiles`, `freeadmin.conf.FreeAdminSettings`, `freeadmin.core.settings.system_config` |
| `freeadmin/middleware.py` | Middleware охраны админки (суперпользователь, сессия) | `starlette` middleware, `freeadmin.conf`, `freeadmin.core.settings`, `freeadmin.boot.admin` |
| `freeadmin/crud.py` | Построитель CRUD-роутов и файлового обмена | `fastapi`, `freeadmin.core` сервисы, `freeadmin.conf`, `freeadmin.core.settings`, `freeadmin.core.services` |
| `freeadmin/api/base.py` | Обёртка системного API админки | `fastapi.APIRouter`, `freeadmin.contrib.adapters.BaseAdapter`, системные API `freeadmin.apps.system.api.views` |
| `freeadmin/orm/config.py` | Конфигурация ORM и жизненный цикл Tortoise | `tortoise` ORM, реестр адаптеров, классификатор ошибок миграций (`freeadmin.utils.migration_errors`) |

## 2. Уровни важности

- **Ядро**: `freeadmin/core/`, `freeadmin/application/`, `freeadmin/boot/`, `freeadmin/hub.py`, `freeadmin/conf.py`, `freeadmin/orm/`, `freeadmin/adapters/`, `freeadmin/models/`. Эти элементы отвечают за конфигурацию, регистрацию ресурсов, связь с ORM и глобальные сервисы.
- **Оболочки**: `freeadmin/api/`, `freeadmin/router/`, `freeadmin/crud.py`, `freeadmin/middleware.py`, `freeadmin/pages/`, `freeadmin/widgets/`, `freeadmin/templates/`, `freeadmin/static/`, `freeadmin/runner.py`, `freeadmin/cli.py`. Модули обеспечивают HTTP-интерфейсы, UI и вспомогательные сценарии.
- **Утилиты**: `freeadmin/utils/`, `freeadmin/schema/`, `freeadmin/tests/`, `freeadmin/provider.py`, `freeadmin/meta.py`. Служебные компоненты и расширяемые помощники.

## 3. Предлагаемая структура (≤ 4 уровня вложенности)

### 3.1 Логика группировки

1. **`core/`** — объединяет доменные сервисы админки, настройки и запуск. Содержит подпакеты `domain/` (текущее содержимое `core/`), `runtime/` (инициализация и хаб), `config/` (настройки и конфигурация), `orm/` (обёртки над ORM) и `adapters/` (интеграции с внешними источниками данных).
2. **`shell/`** — внешний слой, взаимодействующий с FastAPI и фронтендом. Подпакеты `http/` (API, CRUD, маршрутизация, middleware), `presentation/` (страницы, шаблоны, виджеты, статика) и `operations/` (CLI, раннеры).
3. **`support/`** — общие утилиты и схемы. Подпакеты `tooling/` (утилиты, схемы, тесты) и `integration/` (провайдеры ресурсов, дополнительные вспомогательные слои).

### 3.2 Итоговое дерево (предложение)

```
freeadmin/
    core/
        domain/
        runtime/
        config/
        orm/
        adapters/
    shell/
        http/
        presentation/
        operations/
    support/
        tooling/
        integration/
```

### 3.3 Таблица соответствия «исходный путь → целевой путь»

| Исходный путь | Категория | Предлагаемый целевой путь | Комментарий |
| --- | --- | --- | --- |
| `freeadmin/application/factory.py` | Ядро | `freeadmin/core/runtime/application_factory.py` | Фабрика FastAPI становится частью запуска.
| `freeadmin/boot/` | Ядро | `freeadmin/core/runtime/bootstrap/` | Управление адаптерами и моделью запуска переносится в runtime.
| `freeadmin/hub.py` | Ядро | `freeadmin/core/runtime/hub.py` | Централизованный хаб соседствует с фабрикой и BootManager.
| `freeadmin/conf.py` | Ядро | `freeadmin/core/config/settings.py` | Конфигурация переезжает в отдельный пакет настроек.
| `freeadmin/core/` | Ядро | `freeadmin/core/domain/` | Текущее содержимое ядра оформляется как доменный подпакет.
| `freeadmin/orm/` | Ядро | `freeadmin/core/orm/` | Конфигурация ORM входит в ядро.
| `freeadmin/adapters/` | Ядро | `freeadmin/core/adapters/` | Регистрация и реализация адаптеров остаётся рядом с ORM.
| `freeadmin/api/` | Оболочки | `freeadmin/shell/http/api/` | API и совместимость с видом системных эндпоинтов.
| `freeadmin/router/` | Оболочки | `freeadmin/shell/http/router/` | Аггрегаторы и вспомогательные роутеры образуют HTTP-подслой.
| `freeadmin/crud.py` | Оболочки | `freeadmin/shell/http/crud.py` | CRUD остаётся в HTTP-подслое.
| `freeadmin/middleware.py` | Оболочки | `freeadmin/shell/http/middleware.py` | Middleware переносится рядом с роутерами.
| `freeadmin/pages/`, `freeadmin/widgets/`, `freeadmin/templates/`, `freeadmin/static/` | Оболочки | `freeadmin/shell/presentation/{pages,widgets,templates,static}/` | UI-артефакты формируют презентационный слой.
| `freeadmin/cli.py`, `freeadmin/runner.py` | Оболочки | `freeadmin/shell/operations/{cli.py,runner.py}` | Скрипты запуска и CLI собраны в одном подпакете.
| `freeadmin/provider.py` | Утилиты | `freeadmin/support/integration/provider.py` | Поставщик шаблонов выступает вспомогательной интеграцией.
| `freeadmin/utils/`, `freeadmin/schema/`, `freeadmin/tests/`, `freeadmin/meta.py` | Утилиты | `freeadmin/support/tooling/{utils,schema,tests,meta.py}` | Общие помощники и схемы находятся в слое поддержки.

