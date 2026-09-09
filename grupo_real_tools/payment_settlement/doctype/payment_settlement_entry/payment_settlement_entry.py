import frappe
from frappe.model.document import Document
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import getdate


class PaymentSettlementEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from grupo_real_tools.payment_settlement.doctype.payment_settlement_entry_account.payment_settlement_entry_account import PaymentSettlementEntryAccount
		from grupo_real_tools.payment_settlement.doctype.payment_settlement_entry_component.payment_settlement_entry_component import PaymentSettlementEntryComponent
		from grupo_real_tools.payment_settlement.doctype.payment_settlement_entry_reference.payment_settlement_entry_reference import PaymentSettlementEntryReference

		accounts: DF.Table[PaymentSettlementEntryAccount]
		amended_from: DF.Link | None
		company: DF.Link
		components: DF.Table[PaymentSettlementEntryComponent]
		from_date: DF.Datetime
		posting_date: DF.Date
		references: DF.Table[PaymentSettlementEntryReference]
		template: DF.Link
		to_date: DF.Datetime
		total_credit: DF.Currency
		total_debit: DF.Currency
	# end: auto-generated types

	def validate(self):
		self._set_accounts_clearing_totals()

	@frappe.whitelist(allow_guest=False)
	def fetch_template_data(self):
		""" Copy Template Fields """
		self.set('accounts', [])
		self.set('components', [])

		if not self.template:
			return

		template = frappe.get_doc('Payment Settlement Template', self.template)

		self.set('accounts', [{
			'mode_of_payment': account.mode_of_payment,
			'clearing_account': account.clearing_account,
			'clearing_account_currency': account.clearing_account_currency,
			'bank_account': account.bank_account,
			'settlement_account': account.settlement_account,
			'settlement_account_currency': account.settlement_account_currency
		} for account in template.accounts])

		self.set('components', [{
			'account': component.account,
			'account_currency': component.account_currency,
			'calculation_method': component.calculation_method,
			'rate': component.rate,
		} for component in template.components])

	@frappe.whitelist(allow_guest=False)
	def fetch_references(self):
		""" Calculate Reference Docs """
		from_date = getdate(self.from_date)
		to_date = getdate(self.to_date)

		references = []

		for account in self.accounts:
			references.extend(self._get_payment_entry_references(account, from_date, to_date))
			references.extend(self._get_sales_invoice_payment_references(account, from_date, to_date))

		self.set('references', references)
		self._set_accounts_clearing_totals()

	@frappe.whitelist(allow_guest=False)
	def calculate_account_totals(self):
		self._set_accounts_clearing_totals()

	def _set_accounts_clearing_totals(self):
		for account in self.accounts:
			references = [
				reference
				for reference in self.references
				if reference.mode_of_payment == account.mode_of_payment
			]  # Get only References related to Clearing Account(by mode of payment)

			account.reference_count = len(references)
			account.clearing_amount = sum(reference.amount for reference in references)
			account.clearing_base_amount = sum(reference.base_amount for reference in references)

	def _get_payment_entry_references(self, account, from_date, to_date):
		payment_entry = frappe.qb.DocType('Payment Entry')

		references = (
			frappe.qb.from_(payment_entry)
			.select(
				ConstantColumn('Payment Entry').as_('reference_doctype'),
				payment_entry.name.as_('reference_name'),
				payment_entry.posting_date,
				payment_entry.party_type,
				payment_entry.party,
				payment_entry.party_name,
				payment_entry.mode_of_payment,
				payment_entry.paid_to_account_currency.as_('currency'),
				payment_entry.received_amount.as_('amount'),
				payment_entry.base_received_amount.as_('base_amount'),
				payment_entry.reference_no,
			).where(
				(payment_entry.docstatus == 1)
				& (payment_entry.company == self.company)
				& (payment_entry.payment_type == 'Receive')
				& (payment_entry.mode_of_payment == account.mode_of_payment)
				& (payment_entry.paid_to == account.clearing_account)
				& (payment_entry.posting_date >= from_date)
				& (payment_entry.posting_date <= to_date)
			)
			.orderby(payment_entry.posting_date)
			.orderby(payment_entry.name)
		)

		return references.run(as_dict=True)

	def _get_sales_invoice_payment_references(self, account, from_date, to_date):
		sales_invoice = frappe.qb.DocType('Sales Invoice')
		sales_invoice_payment = frappe.qb.DocType('Sales Invoice Payment')

		references = (
			frappe.qb.from_(sales_invoice)
			.inner_join(sales_invoice_payment)
			.on(
				(sales_invoice_payment.parent == sales_invoice.name)
				& (sales_invoice_payment.parenttype == 'Sales Invoice')
			).select(
				ConstantColumn('Sales Invoice').as_('reference_doctype'),
				sales_invoice.name.as_('reference_name'),
				sales_invoice_payment.name.as_('reference_row_name'),
				sales_invoice.posting_date,
				ConstantColumn('Customer').as_('party_type'),
				sales_invoice.customer.as_('party'),
				sales_invoice.customer_name.as_('party_name'),
				sales_invoice_payment.mode_of_payment,
				sales_invoice.currency.as_('currency'),
				sales_invoice_payment.amount.as_('amount'),
				sales_invoice_payment.base_amount.as_('base_amount'),
				sales_invoice_payment.reference_no,
			).where(
				(sales_invoice.docstatus == 1)
				& (sales_invoice.is_return == 0)
				& (sales_invoice.company == self.company)
				& (sales_invoice_payment.mode_of_payment == account.mode_of_payment)
				& (sales_invoice_payment.account == account.clearing_account)
				& (sales_invoice.posting_date >= from_date)
				& (sales_invoice.posting_date <= to_date)
			)
			.orderby(sales_invoice.posting_date)
			.orderby(sales_invoice.name)
			.orderby(sales_invoice_payment.idx)
		)

		return references.run(as_dict=True)
