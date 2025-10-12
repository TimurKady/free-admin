# FastAPI FreeAdmin

Welcome to the FreeAdmin documentation. Use the navigation below to jump to the most common topics.

**FreeAdmin** is a lightweight, framework-agnostic administration system inspired by Django-Admin — rebuilt from the ground up for modern Python backends.

It brings you a **modular**, **declarative**, and **fully customizable** admin interface that works anywhere:  
FastAPI, Tortoise ORM, SQLAlchemy, or even your own data layer.

---

## Why FreeAdmin

FreeAdmin was created to make admin panels **as flexible as your codebase**.  
Instead of tying you to one framework or ORM, it lets you describe your data and UI declaratively — the way you think about business logic, not how a specific web framework does.

- **Universal:** works with any Python web stack or ORM adapter.  
- **Declarative:** define models, widgets, views, and actions in pure Python.  
- **Composable:** every admin page, card, and widget can be extended or replaced.  
- **Fast:** no build step, no React dependency — Bootstrap 5, jQuery, and JSON-Editor out of the box.  
- **Self-contained:** drop into any project and get a complete admin system within minutes.

---

## Core Philosophy

1. **Admin as Metadata** — your admin definitions are pure metadata; the runtime adapts to your backend.
2. **Consistency Over Magic** — clear class contracts (`ModelAdmin`, `InlineAdmin`, `WidgetContext`, `AdminSite`).
3. **Declarative UI** — each component can be rendered or overridden with minimal boilerplate.
4. **Open by Design** — everything is extensible: adapters, routing, widgets, permissions.
5. **Community First** — the project is AGPL-licensed to ensure long-term openness and collaboration.

```
     AdminSite → ModelAdmin → Adapter → ORM → Database
                            ↓
             Forms & Widgets / Views / Cards
```

---

## What You Get

- A fully functional **Admin site** with user menu, cards, settings pages, and permissions.  
- **Automatic CRUD** pages for your models.  
- Built-in widgets powered by **Bootstrap 5**, **Choices.js**, and **JSONEditor**.  
- Seamless integration with **Tortoise ORM**, **FastAPI**, and other frameworks via adapters.  
- A clean, extensible **API layer** for front-end and third-party tools.

---

## Getting Started

Follow the **[Quick Start guide](quick-start.md)** to:
- Create your first FreeAdmin project via CLI
- Configure your `app.py`
- Register a model and admin class
- Launch the admin site in your browser

You can also explore:
- **[Admin Architecture](admin/ADMIN.md)** — how the system is structured internally
- **[Widgets](admin/widgets.md)** — ready-to-use UI components
- **[System Settings](admin/settings.md)** — managing configuration at runtime

---

## Road Ahead

FreeAdmin is still evolving. The near-term roadmap includes:
- More built-in widgets and cards
- Optional dark theme
- Improved API documentation
- Integration examples for SQLAlchemy and Peewee
- Enhanced role-based permissions and audit logging

Join the journey — explore, adapt

