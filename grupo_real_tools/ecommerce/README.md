# Ecommerce

This module exposes the read-only ERPNext catalog projection used by the Vue storefront. Product availability comes
from the default company's warehouse, and prices use the selling price list configured in ERPNext.

## Public API

Use Frappe API v2 for browser requests:

```text
GET /api/v2/method/grupo_real_tools.ecommerce.api.item.get_items
GET /api/v2/method/grupo_real_tools.ecommerce.api.item.get_items_from_template
GET /api/v2/method/grupo_real_tools.ecommerce.api.item_group.get_item_groups
GET /api/v2/method/grupo_real_tools.ecommerce.api.item_attribute.get_item_attributes
```

Frappe API v2 returns method results under the `data` response property. The files under `api/` define the public
surface by primary ERPNext resource. `catalog.py` retains the catalog composition and query implementation.

`catalog_api.py` and the whitelisted methods historically exposed by `catalog.py` remain temporary compatibility
surfaces while deployed consumers migrate. Do not add new consumers to those paths.

## Verification

Run the Ecommerce tests through the repository's Frappe/Bench environment. Syntax checks alone do not verify stock,
pricing, category descendants or response contracts against ERPNext.
