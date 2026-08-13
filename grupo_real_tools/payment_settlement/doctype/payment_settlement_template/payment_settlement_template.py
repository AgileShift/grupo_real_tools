from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from frappe.model.document import Document


class PaymentSettlementTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from grupo_real_tools.payment_settlement.doctype.payment_settlement_template_account.payment_settlement_template_account import PaymentSettlementTemplateAccount
		from grupo_real_tools.payment_settlement.doctype.payment_settlement_template_component.payment_settlement_template_component import PaymentSettlementTemplateComponent

		accounts: DF.Table[PaymentSettlementTemplateAccount]
		company: DF.Link
		components: DF.Table[PaymentSettlementTemplateComponent]
	# end: auto-generated types

	def before_validate(self):
		for account in self.accounts:
			account.clearing_account = get_bank_cash_account(account.mode_of_payment, self.company).get('account')
