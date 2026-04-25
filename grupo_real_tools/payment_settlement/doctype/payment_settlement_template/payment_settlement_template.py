from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from frappe.model.document import Document


class PaymentSettlementTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from grupo_real_tools.payment_settlement.doctype.payment_settlement_template_component.payment_settlement_template_component import PaymentSettlementTemplateComponent

		bank_account: DF.Link | None
		clearing_account: DF.Link | None
		company: DF.Link
		components: DF.Table[PaymentSettlementTemplateComponent]
		mode_of_payment: DF.Link
		settlement_account: DF.Link
	# end: auto-generated types

	def before_validate(self):
		self.clearing_account = get_bank_cash_account(self.mode_of_payment, self.company).get('account')
