# FreeAdmin Public Page Authoring Guide

## Introduction
FreeAdmin public pages let you showcase product capabilities to unauthenticated visitors while retaining the admin portal's cohesive look and feel. This guide walks through the complete lifecycle of building a page—from architectural setup and data modeling to integrations, templating, navigation, and publication.

## Page Architecture
1. **Inherit the base class.** Derive your page from `BaseTemplatePage` so that the instance reuses the admin site's configuration and lifecycle hooks.
   ```python
   from freeadmin.ui.pages import BaseTemplatePage

   class MarketingLanding(BaseTemplatePage):
       path = "/marketing"
       name = "Marketing"
       icon = "mdi-bullhorn"
       template = "marketing/landing.html"
       template_directory = "marketing"

       def __init__(self, admin_site):
           super().__init__(admin_site)
   ```
2. **Lock in routing attributes.** Declare `path`, `name`, `icon`, `template`, and `template_directory` at class level. FreeAdmin reads them during registration to wire routing and template resolution.
3. **Override `register`.** Call `register_public_view` inside `register` to expose the page through the public router.
   ```python
   def register(self):
       super().register()
       self.admin_site.register_public_view(self.path, self)
   ```

## Content Modeling
1. **Immutable containers.** Define a `@dataclass(frozen=True)` for every logical section to keep template contracts explicit and prevent accidental mutation.
   ```python
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class FeatureCard:
       title: str
       description: str
       icon: str
   ```
2. **Encapsulated builders.** Create private builders such as `_build_feature_cards` that return tuples of dataclass instances. Builders are easy to test and reuse.
   ```python
   class MarketingLanding(BaseTemplatePage):
       ...

       def _build_feature_cards(self) -> tuple[FeatureCard, ...]:
           return (
               FeatureCard(
                   title="Analytics",
                   description="Campaign metrics refresh in real time.",
                   icon="mdi-chart-areaspline",
               ),
               FeatureCard(
                   title="Automation",
                   description="Lead nurturing scenarios run on schedule.",
                   icon="mdi-robot",
               ),
           )
   ```
3. **Property accessors.** Expose builders through properties so the public API stays clear and caching can be added later.
   ```python
   class MarketingLanding(BaseTemplatePage):
       ...

       @property
       def feature_cards(self) -> tuple[FeatureCard, ...]:
           return self._build_feature_cards()
   ```

## Working with Data
1. **Static content.** For landing pages that do not hit external services, assemble the data directly inside builders.
   ```python
   class MarketingLanding(BaseTemplatePage):
       ...

       def _build_faq(self) -> tuple[FeatureCard, ...]:
           return (
               FeatureCard(
                   title="How do I get started?",
                   description="Submit the onboarding form and our team will enable the workspace within one business day.",
                   icon="mdi-rocket-launch",
               ),
               FeatureCard(
                   title="Is there a free tier?",
                   description="Yes, FreeAdmin offers a community plan with core analytics and dashboards.",
                   icon="mdi-gift",
               ),
           )
   ```
2. **Service integrations.** Wrap database or API access in dedicated service classes when the data is dynamic.
   ```python
   class CaseStudyService:
       """Delivers customer case studies for public pages."""

       def __init__(self, repository):
           self._repository = repository

       async def fetch_cases(self) -> tuple[dict, ...]:
           cases = await self._repository.list_latest()
           if not cases:
               return ({"title": "Updates coming soon", "summary": "Check back for new success stories."},)
           return tuple({"title": case.name, "summary": case.summary} for case in cases)
   ```
3. **Asynchronous resilience.** Prefer asynchronous methods for I/O and provide fallback data so the page stays available even when external systems fail.

## Template Context
1. **Context assembly.** Override `get_context` and return a single dictionary containing collections, metadata, and the request-bound objects your template expects.
   ```python
   class MarketingLanding(BaseTemplatePage):
       ...

       def get_context(self, request):
           return {
               "request": request,
               "user": request.user,
               "page_title": "Marketing Portal",
               "hero": {
                   "title": "Unlock FreeAdmin's potential",
                   "subtitle": "Growth tooling for your entire team",
               },
               "feature_sections": self.feature_cards,
           }
   ```
2. **Descriptive keys.** Use expressive names such as `feature_sections`, `pipeline_flow`, and `observability_signals` to keep the contract between Python and Jinja obvious.
3. **Consistent extensibility.** When you add a new section, follow the same pattern: dataclass → builder → property → context entry → template loop.

## Navigation and Menus
1. **Menu registration.** Implement `public_menu` to aggregate `MenuItem` instances from the registered public views.
   ```python
   from freeadmin.ui.menu import MenuItem

   class MarketingLanding(BaseTemplatePage):
       ...

       def public_menu(self) -> tuple[MenuItem, ...]:
           return tuple(
               MenuItem(path=view.path, label=view.name, icon=view.icon)
               for view in self.admin_site.public_views
           )
   ```
2. **Consistent navigation.** Iterate over registered descriptors so visitors experience a unified set of landing pages.

## Templates
1. **Structured blocks.** Break the template into blocks—hero, benefits, stages, signals, call to action—to support reuse across multiple pages.
2. **Jinja loops.** Iterate over dataclass collections when rendering.
   ```jinja
   {% for card in feature_sections %}
     <section class="feature">
       <i class="{{ card.icon }}"></i>
       <h3>{{ card.title }}</h3>
       <p>{{ card.description }}</p>
     </section>
   {% endfor %}
   ```
3. **Aligned naming.** Keep context keys synchronized with section names to prevent drift between Python logic and templates.

## Extensibility and Reuse
1. **Adding sections.** Repeat the established pattern whenever you introduce a new block.
2. **Shared services.** Extract reusable integrations into service classes with clear interfaces and fallback behavior to avoid duplicated code across pages.
3. **Caching strategies.** Cache immutable sections and prefer lazy loading for expensive queries.

## Database Integration
1. **Data services.** Create access layers that convert database or CMS records into dataclasses.
   ```python
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class CustomerStory:
       title: str
       result: str
       link: str

   class CustomerStoryService:
       """Returns customer stories for public landings."""

       def __init__(self, repository):
           self._repository = repository

       async def fetch(self) -> tuple[CustomerStory, ...]:
           stories = await self._repository.list_published()
           if not stories:
               return (
                   CustomerStory(
                       title="New stories in progress",
                       result="We will share fresh wins soon.",
                       link="#",
                   ),
               )
           return tuple(
               CustomerStory(title=story.title, result=story.result, link=story.url)
               for story in stories
           )
   ```
2. **Performance.** Keep heavy queries out of `get_context`, cache infrequently changing data, and defer expensive lookups until they are truly needed.

## Review and Publication
1. **Local verification.** Start the FreeAdmin server locally and open the page in a browser before publishing.
2. **Documentation hygiene.** Maintain up-to-date descriptions of contexts and templates so the team can evolve pages quickly.
3. **Go-live checklist.** After registration, confirm that the page appears in the public router and loads without authentication.

## Conclusion
By following this architecture—dataclasses for content, service classes for integrations, and a consistent context-building pattern—you can deliver resilient, extensible public pages in FreeAdmin while keeping the visitor experience aligned across the product.
