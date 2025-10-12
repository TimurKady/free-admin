# Dashboard Cards

## Configuring Card Width

You can control the width of cards in two ways:

1. **Via card registration** — provide the grid class when calling `register_card`:

   ```python
   admin_site.register_card(
       key="thermo1",
       label="Demo",
       title="Temperature Sensor",
       template="cards/thermo.html",
       col_class="col-2"
   )
   ```

2. **Via the card template** — override the `card_col_class` block in a template that extends `includes/cards.html`:

   ```jinja2
   {% extends "includes/cards.html" %}
   {% block card_col_class %}col-2{% endblock %}
   {% block card_body %}
    Temperature: — °C
   {% endblock %}
   ```

If the `card_col_class` block is defined inside the card template, it takes priority and overrides the `col_class` specified during registration. Otherwise the value from registration is used (`col-2` by default, which renders six cards per row).

<!-- # The End -->
