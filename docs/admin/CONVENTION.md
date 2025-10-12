## Project Folder and Naming Convention

This convention defines how to organize source code and name files and directories within the `cortex/` project to ensure modularity, clarity, and maintainability.

---

### 1. Folder = Functional Module

Each **top-level folder** inside `apps/` represents a **separate functional module** (e.g., `agents/`, `streams/`, `sessions/`, `api/`, `utils/`).

* All code, logic, models, tasks, and interfaces related to a feature should reside **inside that folder**.
* Cross-cutting concerns (like `utils`, `config`, other) may live separately but should follow the same internal rules.

---

### 2. File Naming Convention inside a Module

Each module may contain a subset of the following files or subfolders:

| Filename or folder               | Purpose                                                           |
| -------------------------------- | ----------------------------------------------------------------- |
| `__init__.py`                    | Makes the folder a Python package                                 |
| `<module_name>.py`               | Main logic or core classes                                        |
| `models.py` or `models/`         | ORM models for the module                                         |
| `admin.py` or `admin/`           | Admin logic or forms (if applicable)                              |
| `schemas.py` or `schemas/`       | Pydantic / Marshmallow data schemas                               |
| `routers.py` or `routers/`       | FastAPI routers related to this module                            |
| `services.py` or services/       | Support logic or internal helpers                                 |
| `validators.py` or `validators/` | Input validation logic (optional)                                 |
| `widgets.py` or `widgets/`       | Form field widgets                                                |
| `core.py` or `core/`             | Key objects, the root logic of the package                        |
| `api.py` or `api/`               | REST or WebSocket endpoint logic                                  |
| `tasks.py` or `tasks/`           | Celery tasks owned by this module                                 |
| `utils.py` or `utils/`           | Auxiliary objects, functions that are not included in other logic |

For the admin package, place core classes such as ``ModelAdmin`` and
``InlineModelAdmin`` inside an ``admin/core/`` folder and keep temporary helper
functions in ``admin/utils/``.
ect.

> In general, one can follow Django's logic.
> Only include files that are relevant — skip unused ones.

---

### 3. Agents

* All AI agents live under `agents/`:

  ```
  agents/
  ├── admin/
  ├── analyzer/
  └── ...
  ```
* Each agent submodule follows the same convention:

  ```
  analyzer/
  ├── analyzer.py
  ├── tasks.py
  └── schema.py
  ```

---

### 4. Import Rules

* Use relative imports inside the same module (`from .schema import InputDataSchema`)

* All imports between modules should follow **absolute pathing** from the `cortex.` root, respecting `PYTHONPATH=/app`:

  ```python
  from cortex.agents.analyzer.analyzer import AnalyzerAgent
  from cortex.selector.rules import RuleEngine
  ```
* Avoid circular imports; use function-level imports when needed.


---

### 5. Configuration

* Project-wide settings, `.env` parsing, and logging setup go in `config/`
* Never hardcode paths or secrets — use environment variables and config objects

---

### 6. Documentation

* High-level diagrams and descriptions belong in:

  * `README.md` — overview
  * `CONVENTIONS.md` — this file
  * `docs/architecture.md` — system pipeline and module map
