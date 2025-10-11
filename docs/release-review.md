# Release compliance checklist

## Vendor license verification

All bundled frontend libraries ship their upstream license text:

- Bootstrap 5.3.3 — `freeadmin/static/vendors/bootstrap/LICENSE`
- Bootstrap Icons 1.11.3 — `freeadmin/static/vendors/bootstrap-icons/LICENSE`
- jQuery 3.7.1 — `freeadmin/static/vendors/jquery/LICENSE.txt`
- JsBarcode 3.12.1 — `freeadmin/static/vendors/jsbarcode/LICENSE`
- Select2 4.0.13 — `freeadmin/static/vendors/select2/LICENSE`
- Choices.js 11.1.0 — `freeadmin/static/vendors/choices/LICENSE`
- Ace builds 1.43.3 — `freeadmin/static/vendors/ace-builds/LICENSE`
- JSONEditor 9.x — `freeadmin/static/vendors/json-editor/LICENSE`

If a vendor is updated, replace the assets and refresh the license file at the same path.

## Size spot-checks

- Static bundle footprint: `du -sh freeadmin/static` → ~37 MB.
- Build artifacts (`python -m build`):
  - Wheel: `dist/freeadmin-0.1.0-py3-none-any.whl` ≈ 7.7 MB.
  - Source archive: `dist/freeadmin-0.1.0.tar.gz` ≈ 6.2 MB.

These numbers provide a baseline for future reviews. Investigate any large deltas and consider trimming optional Ace modes or JSONEditor test fixtures if distribution size becomes an issue.
