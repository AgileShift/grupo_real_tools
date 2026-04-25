from frappe.model.document import Document


class PaymentSettlementEntryComponent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link
		calculation_method: DF.Literal["", "Percentage", "Fixed Amount", "Manual"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate: DF.Percent
	# end: auto-generated types

	pass
