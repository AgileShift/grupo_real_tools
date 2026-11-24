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

Frappe API v2 returns method results under the `data` response property.
The files under `api/` define the public surface by primary ERPNext resource.

Listing and detail return variant `attributes` keyed by the exact ERPNext attribute name. Each entry contains
`value` and `abbr` from the configured list values. The storefront catalog uses non-numeric Item Attributes.

Only functions under `ecommerce/api` are whitelisted.

## Verification

Run the Ecommerce tests through the repository's Frappe/Bench environment. Syntax checks alone do not verify stock,
pricing, category descendants or response contracts against ERPNext.
