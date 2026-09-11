import frappe
from erpnext.setup.utils import get_exchange_rate
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import flt, getdate


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
		journal_entry: DF.Link | None
		posting_date: DF.Date
		references: DF.Table[PaymentSettlementEntryReference]
		template: DF.Link
		to_date: DF.Datetime
		total_credit: DF.Currency
		total_debit: DF.Currency
	# end: auto-generated types

	def validate(self):
		# _validate_links() -> Any submittable link(in doc or children) throws invalid if canceled
		self.calculate()

	def before_submit(self):
		self._validate_settled_references()

		if self.difference:
			frappe.throw(_('Total Debit must be equal to Total Credit. The difference is {0}').format(self.difference))

	def on_submit(self):
		journal = frappe.new_doc(
			'Journal Entry',
			company=self.company,
			posting_date=self.posting_date,
			voucher_type='Journal Entry',
			multi_currency=True,
			custom_remark=True,
			remark=_('Payment Settlement Entry') + f': {self.name}',
		)

		for component in self.components:
			if not (component.debit_in_account_currency or component.credit_in_account_currency):
				continue  # Skip Empty Components

			journal.append('accounts', {
				'account': component.account,
				'exchange_rate': component.exchange_rate,
				'debit_in_account_currency': component.debit_in_account_currency,
				'credit_in_account_currency': component.credit_in_account_currency,
				'user_remark': component.user_remark,
			})
		journal.insert()

		# ERPNext recalculates its own amounts; do not post a different closure silently.
		for component, row in zip(
			[c for c in self.components if c.debit_in_account_currency or c.credit_in_account_currency], journal.accounts,
		):
			if row.debit != component.debit or row.credit != component.credit:
				frappe.throw(
					_('The Journal Entry calculates different amounts for {0}. Check the exchange rate and precision.')
					.format(component.account)
				)

		journal.submit()
		self.db_set('journal_entry', journal.name)

	def on_cancel(self):
		if self.journal_entry:
			journal = frappe.get_doc('Journal Entry', self.journal_entry)
			if journal.docstatus == 1:
				journal.cancel()
			elif journal.docstatus != 2:
				frappe.throw(_('The linked Journal Entry is neither submitted nor cancelled.'))

	@property
	def difference(self):
		return flt(self.total_debit - self.total_credit, self.precision('difference'))

	@frappe.whitelist()
	def make_difference(self, adjustment_type: str):
		account_fields = {
			'Round Off': 'round_off_account',
			'Exchange Gain Or Loss': 'exchange_gain_loss_account',
			'Write Off': 'write_off_account',
		}

		if adjustment_type not in account_fields:
			frappe.throw(_('Invalid Option'))

		self.calculate()
		if not self.difference:
			return

		if not (account := frappe.get_cached_value('Company', self.company, account_fields[adjustment_type])):
			frappe.throw(_("Please set '{0}' in Company: {1}").format(adjustment_type, self.company))

		self.append('components', {
			'type': 'Adjustment',
			'calculation_method': 'Manual',
			'account': account,
			'account_currency': frappe.get_cached_value('Account', account, 'account_currency'),
			'debit_in_account_currency': max(-self.difference, 0),
			'credit_in_account_currency': max(self.difference, 0),
			'user_remark': adjustment_type,
		})

		self.calculate()

	@frappe.whitelist(allow_guest=False)
	def fetch_template_data(self):
		""" Copy Template Values as Skeleton """
		if not self.template:
			self.set('accounts', [])
			self.set('components', [])
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

		clearing_accounts, settlement_accounts = [], []
		for account in template.accounts:
			clearing_accounts.append({
				'account': account.clearing_account,
				'account_currency': account.clearing_account_currency,
				'calculation_method': 'Manual', 'type': 'Clearing'
			})

			settlement_accounts.append({
				'account': account.settlement_account,
				'account_currency': account.settlement_account_currency,
				'calculation_method': 'Manual', 'type': 'Settlement'
			})

		self.set('components', clearing_accounts + [{
			'account': component.account,
			'account_currency': component.account_currency,
			'calculation_method': component.calculation_method,
			'rate': component.rate,
			'apply_to': component.apply_to,
			'type': 'Component',
		} for component in template.components] + settlement_accounts)

	@frappe.whitelist(allow_guest=False)
	def fetch_references(self):
		""" Get Reference Docs """
		from_date = getdate(self.from_date)
		to_date = getdate(self.to_date)

		references = []
		for account in self.accounts:
			references.extend(self._get_payment_entry_references(account, from_date, to_date))
			references.extend(self._get_sales_invoice_payment_references(account, from_date, to_date))

		candidate_names = {row.reference_name for row in references}
		settled = {
			(row.reference_doctype, row.reference_name, row.reference_row_name or '')
			for row in frappe.get_all(
				'Payment Settlement Entry Reference',
				filters={'docstatus': 1, 'parenttype': self.doctype, 'reference_name': ['in', candidate_names]},
				fields=['reference_doctype', 'reference_name', 'reference_row_name']
			)
		} if candidate_names else set()  # Query only matching References

		self.set('references', [
			row for row in references
			if (row.reference_doctype, row.reference_name, row.reference_row_name or '') not in settled
		])
		self.calculate()

	@frappe.whitelist(allow_guest=False)
	def calculate(self):
		self._calculate_clearing_components()
		self._set_component_exchange_rates()
		self._calculate_settlement_components()

		# Calculate doc totals
		self.total_debit = flt(sum(row.debit for row in self.components), self.precision('total_debit'))
		self.total_credit = flt(sum(row.credit for row in self.components), self.precision('total_credit'))

	def _validate_settled_references(self):
		reference_keys = {(
			reference.reference_doctype,
			reference.reference_name,
			reference.reference_row_name or '',
		) for reference in self.references}

		settled_references = frappe.db.get_all(
			'Payment Settlement Entry Reference',
			filters={
				'reference_name': ['in', {reference.reference_name for reference in self.references}],
				'docstatus': 1,
				'parent': ['!=', self.name], 'parenttype': self.doctype,
			},
			fields=['reference_doctype', 'reference_name', 'reference_row_name', 'parent'],
		)

		for reference in settled_references:
			key = (
				reference.reference_doctype,
				reference.reference_name,
				reference.reference_row_name or '',
			)

			if key in reference_keys:
				frappe.throw(
					_('{0} was already settled in {1}.').format(
						reference.reference_name, reference.parent
					)
				)

	def _calculate_clearing_components(self):
		for account in self.accounts:
			references = [
				reference
				for reference in self.references
				if reference.mode_of_payment == account.mode_of_payment
			]  # Get only References related to Clearing Account(by mode of payment)

			account.reference_count = len(references)
			account.clearing_amount = sum(reference.amount for reference in references)
			account.clearing_base_amount = sum(reference.base_amount for reference in references)

			for component in self.components:  # Calculate Clearing Values for Components Table
				if component.type == 'Clearing' and component.account == account.clearing_account:
					component.debit, component.debit_in_account_currency = 0, 0
					component.credit = flt(account.clearing_base_amount, component.precision('credit'))
					component.credit_in_account_currency = flt(
						account.clearing_amount, component.precision('credit_in_account_currency')
					)
					break  # Match each existing clearing row only once.

	def _set_component_exchange_rates(self):
		if not self.posting_date:
			return

		company_currency = frappe.get_cached_value('Company', self.company, 'default_currency')
		rates = {}

		for component in self.components:
			if component.type == 'Clearing':  # Auto Calculate -> is an aggregate of all the references
				component.exchange_rate = (
					component.credit / component.credit_in_account_currency if component.credit_in_account_currency else 0
				)
				continue
			elif component.account_currency == company_currency:
				component.exchange_rate = 1
			elif not component.exchange_rate:
				if component.account_currency not in rates:
					rates[component.account_currency] = get_exchange_rate(
						component.account_currency, company_currency, self.posting_date
					)
				component.exchange_rate = rates[component.account_currency]

			# Calculate internal component values
			self._calculate_component_base_amounts(component)

	@staticmethod
	def _calculate_component_base_amounts(component):
		component.debit_in_account_currency = flt(
			component.debit_in_account_currency, component.precision('debit_in_account_currency')
		)
		component.credit_in_account_currency = flt(
			component.credit_in_account_currency, component.precision('credit_in_account_currency')
		)
		component.debit = flt(
			component.debit_in_account_currency * component.exchange_rate, component.precision('debit')
		)
		component.credit = flt(
			component.credit_in_account_currency * component.exchange_rate, component.precision('credit')
		)

	def _calculate_settlement_components(self):
		settlements = {}
		clearing_accounts = {}
		settlement_components = {}

		for component in self.components:
			if component.type == 'Settlement':
				if component.override:
					previous = settlement_components.get(component.account)
					if previous and previous.override:
						frappe.throw(_('Only one row can override {0}.').format(component.account))
					settlement_components[component.account] = component
				else:
					settlement_components.setdefault(component.account, component)

		for account in self.accounts:
			clearing_accounts[account.clearing_account] = account.settlement_account
			settlement = settlement_components.get(account.settlement_account)
			if not settlement:
				frappe.throw(_('Missing settlement component for {0}.').format(account.settlement_account))
			if not settlement.exchange_rate or settlement.exchange_rate <= 0:
				frappe.throw(_('Row {0}: a valid exchange rate is required.').format(settlement.idx))

			# Keep the operational balance in the destination account currency.
			if account.clearing_account_currency == settlement.account_currency:
				amount = account.clearing_amount
			else:
				amount = account.clearing_base_amount / settlement.exchange_rate
			settlements.setdefault(account.settlement_account, 0)
			settlements[account.settlement_account] += amount

		for component in self.components:
			if component.type not in ('Component', 'Manual'):
				continue

			adjustment = component.debit_in_account_currency - component.credit_in_account_currency
			if not adjustment:
				continue

			if component.apply_to:
				settlement_account = clearing_accounts.get(component.apply_to)
				if not settlement_account:
					frappe.throw(
						_('Row {0}: Apply To does not belong to this settlement.').format(component.idx)
					)
			elif len(settlements) == 1:
				settlement_account = next(iter(settlements))
			else:
				frappe.throw(
					_('Row {0}: select Apply To because the settlement has multiple destinations.')
					.format(component.idx)
				)

			settlement = settlement_components[settlement_account]
			if component.account_currency != settlement.account_currency:
				if not component.exchange_rate or component.exchange_rate <= 0:
					frappe.throw(_('Row {0}: a valid exchange rate is required.').format(component.idx))
				adjustment = (component.debit - component.credit) / settlement.exchange_rate

			settlements[settlement_account] -= adjustment

		for component in self.components:
			if component.type != 'Settlement' or component.account not in settlements:
				continue

			if component is not settlement_components[component.account]:
				component.debit_in_account_currency = 0
				component.credit_in_account_currency = 0
			elif not component.override:
				balance = settlements[component.account]
				component.debit_in_account_currency = max(balance, 0)
				component.credit_in_account_currency = max(-balance, 0)
			# Base amounts may leave an exchange difference; do not alter the cash balance to hide it.
			self._calculate_component_base_amounts(component)

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
				payment_entry.target_exchange_rate.as_('exchange_rate'),
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
				sales_invoice.currency,
				sales_invoice.conversion_rate.as_('exchange_rate'),
				sales_invoice_payment.amount,
				sales_invoice_payment.base_amount,
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
 # 464 -> i18n plus _validate_links(self) | 8 19
