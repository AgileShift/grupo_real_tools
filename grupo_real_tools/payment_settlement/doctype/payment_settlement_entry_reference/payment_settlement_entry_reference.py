from frappe.model.document import Document


class PaymentSettlementEntryReference(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		base_amount: DF.Currency
		currency: DF.Link
		mode_of_payment: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink | None
		party_name: DF.Data | None
		party_type: DF.Link | None
		posting_date: DF.Date
		reference_doctype: DF.Link
		reference_name: DF.DynamicLink
		reference_no: DF.Data | None
		reference_row_name: DF.Data | None
	# end: auto-generated types

	pass
