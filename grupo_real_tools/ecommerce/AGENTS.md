# Ecommerce module instructions

These instructions extend the repository root `AGENTS.md` for `grupo_real_tools/ecommerce`.

- Keep the public API grouped by the primary ERPNext resource under `ecommerce/api`.
- Expose browser-facing functions only with explicit `frappe.whitelist` and allowed HTTP methods.
- Keep response contracts stable while compatibility endpoints remain deployed.
- Treat Item, stock, price, category, attribute and media data as read-only catalog projections.
- Use controlled fixtures and mocks for verification. Do not query or modify production business data.
- Update this module's README when public method paths or response contracts change.
