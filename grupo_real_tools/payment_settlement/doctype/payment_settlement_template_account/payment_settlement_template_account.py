from frappe.model.document import Document


class PaymentSettlementTemplateAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bank_account: DF.Link | None
		clearing_account: DF.Link | None
		mode_of_payment: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		settlement_account: DF.Link
	# end: auto-generated types

	pass
