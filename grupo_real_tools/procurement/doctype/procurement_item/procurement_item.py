# Copyright (c) 2026, Agile Shift and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ProcurementItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attributes: DF.Data | None
		attributes_json: DF.JSON | None
		has_variants: DF.Check
		item_code: DF.Data
		item_group: DF.Link
		item_name: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass
