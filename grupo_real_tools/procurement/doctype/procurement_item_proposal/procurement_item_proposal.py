from frappe.model.document import Document


class ProcurementItemProposal(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attributes: DF.Data | None
		attributes_json: DF.JSON | None
		item_code: DF.Data
		item_name: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		purchase_rate: DF.Currency
		qty: DF.Int
		selling_rate: DF.Currency
		source_item_code: DF.Data
		subtotal: DF.Currency
	# end: auto-generated types

	pass
