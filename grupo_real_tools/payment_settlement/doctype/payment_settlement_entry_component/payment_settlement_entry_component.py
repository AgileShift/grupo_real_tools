from frappe.model.document import Document


class PaymentSettlementEntryComponent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link
		account_currency: DF.Link | None
		apply_to: DF.Link | None
		bank_account: DF.Link | None
		calculation_method: DF.Literal["", "Manual", "Percentage", "Fixed Amount"]
		credit: DF.Currency
		credit_in_account_currency: DF.Currency
		debit: DF.Currency
		debit_in_account_currency: DF.Currency
		exchange_rate: DF.Float
		override: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate: DF.Percent
		type: DF.Literal["Manual", "Clearing", "Settlement", "Component", "Adjustment"]
		user_remark: DF.SmallText | None
	# end: auto-generated types

	pass
