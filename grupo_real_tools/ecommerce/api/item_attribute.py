import frappe
from frappe.utils.caching import http_cache, redis_cache


@frappe.whitelist(allow_guest=True, methods=["GET"])
@http_cache(public=True, max_age=3000, stale_while_revalidate=3600)
@redis_cache(ttl=3000, user=None, shared=False)
def get_item_attributes(attribute: str):
	""" Returns Item Attribute Values as Requested as a nested tree. """
	rows = frappe.get_all(
		"Item Attribute Value",
		filters={
			"parent": attribute,
			"parenttype": "Item Attribute",
		},
		fields=["attribute_value as value", "abbr", "idx"],
		order_by="abbr, idx",
	)

	return [{"value": row.value, "abbr": row.abbr} for row in rows]
