"""Public Item Group endpoints for the ecommerce catalog."""

import frappe

from grupo_real_tools.ecommerce import catalog


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_item_groups():
	return catalog.get_item_groups()
