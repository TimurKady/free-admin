# Inlines

## TL;DR
- Inline admin components allow editing of related objects directly within the parent form.
- Each inline specifies its model, fields, and rendering options.

## Setup Steps
1. Define an inline class by subclassing the provided inline base.
2. Register the inline with its parent admin class.
3. Include required templates and static assets for dynamic form management.

## Security Notes
- Validate permissions for both parent and inline models.
- Limit exposed fields to prevent mass-assignment vulnerabilities.
- Constrain querysets to the active user's data scope.

## Frontend Contracts
- Inline forms submit nested payloads keyed by the inline prefix.
- Each entry carries its `id`, field values, and a `DELETE` flag when removed.
- Server responses echo serialized inline objects using the same structure.

## Troubleshooting Tips
- Missing inlines often indicate incomplete management form data.
- If add/remove buttons fail, ensure the inline JavaScript bundle is loaded.
- Review permission mixins when inline objects do not appear for certain users.

## Testing Checklist
- [ ] Rendering displays at least one empty inline form.
- [ ] Creating and updating inline items persists data correctly.
- [ ] Validation errors appear next to the affected inline fields.
- [ ] Unauthorized users cannot view or modify restricted inlines.
