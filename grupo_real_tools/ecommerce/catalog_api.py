"""Compatibility routes for consumers migrating to ``ecommerce.api``."""

import frappe

from grupo_real_tools.ecommerce.api import item, item_attribute, item_group


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_items(sale: bool = False, category: str = "", size: str = "", color: str = "", start: int = 0, limit: int = 19):
	return item.get_items(sale=sale, category=category, size=size, color=color, start=start, limit=limit)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_items_from_template(item_code: str):
	return item.get_items_from_template(item_code)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_item_groups():
	return item_group.get_item_groups()


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_item_attributes(attribute: str):
	return item_attribute.get_item_attributes(attribute)
