"""Public Item endpoints for the ecommerce catalog."""

import frappe

from grupo_real_tools.ecommerce import catalog


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_items(
	sale: bool = False,
	category: str = "",
	size: str = "",
	color: str = "",
	start: int = 0,
	limit: int = 19,
):
	return catalog.get_items(
		sale=sale,
		category=category,
		size=size,
		color=color,
		start=start,
		limit=limit,
	)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_items_from_template(item_code: str):
	return catalog.get_items_from_template(item_code)
