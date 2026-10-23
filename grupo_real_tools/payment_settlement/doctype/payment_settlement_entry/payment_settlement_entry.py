import frappe
from erpnext.setup.utils import get_exchange_rate
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from .references import get_references, get_settled_references


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
		naming_series: DF.Literal["PS-.YYYY.-.#####"]
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
			multi_currency=True, custom_remark=True,
			remark=_('Payment Settlement Entry') + f': {self.name}',
		)

		for component in self.components:
			if not (component.debit_in_account_currency or component.credit_in_account_currency):
				continue  # Skip Empty Components

			journal.append('accounts', {
				'account': component.account,
				'bank_account': component.bank_account,
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

	def on_trash(self):
		if self.journal_entry and not frappe.get_single_value('Accounts Settings', 'delete_linked_ledger_entries'):
			frappe.throw(
				_('Please enable {0} in the {1}.').format(
					_('Delete Accounting and Stock Ledger entries on deletion of transaction'),
					_('Accounts Settings'),
				)
			)

	def after_delete(self):
		if self.journal_entry:
			frappe.delete_doc('Journal Entry', self.journal_entry, ignore_missing=False)

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

		template = frappe.get_cached_doc('Payment Settlement Template', self.template)

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
				'calculation_method': 'Automatic', 'type': 'Clearing'
			})

			settlement_accounts.append({
				'account': account.settlement_account,
				'account_currency': account.settlement_account_currency,
				'bank_account': account.bank_account,
				'calculation_method': 'Automatic', 'type': 'Settlement'
			})

		self.set('components', clearing_accounts + [{
			'account': component.account,
			'account_currency': component.account_currency,
			'calculation_method': component.calculation_method,
			'add_deduct_tax': component.add_deduct_tax,
			'rate': component.rate,
			'apply_to': component.apply_to,
			'type': 'Component',
		} for component in template.components] + settlement_accounts)

	@frappe.whitelist(allow_guest=False)
	def fetch_references(self):
		"""Replace the reference snapshot and recalculate the Settlement."""
		self.set('references', get_references(self.company, self.accounts, self.from_date, self.to_date))
		self.calculate()

	@frappe.whitelist(allow_guest=False)
	def calculate(self):
		self._validate_required_components()
		self._validate_component_calculation_methods()
		self.set_bank_accounts()
		self._calculate_clearing_components()
		self._calculate_percentage_components()
		self._set_component_exchange_rates()
		self._calculate_settlement_components()

		# Calculate doc totals
		self.total_debit = flt(sum(row.debit for row in self.components), self.precision('total_debit'))
		self.total_credit = flt(sum(row.credit for row in self.components), self.precision('total_credit'))

	@frappe.whitelist(allow_guest=False)
	def set_bank_accounts(self) -> None:
		for component in self.components:
			if component.type != 'Manual':
				continue

			component.bank_account = frappe.db.get_value('Bank Account', {
				'company': self.company, 'is_company_account': 1, 'account': component.account, 'disabled': 0
			}) if component.account and self.company else None

	def _validate_settled_references(self) -> None:
		candidate_names = {reference.reference_name for reference in self.references}
		settled = get_settled_references(candidate_names)

		for reference in self.references:
			key = (reference.reference_doctype, reference.reference_name, reference.reference_row_name or '')

			if key in settled:
				frappe.throw(
					_('{0} was already settled in {1}.').format(reference.reference_name, settled[key])
				)

	def _validate_required_components(self) -> None:
		present = {(component.type, component.account) for component in self.components}

		for account in self.accounts:
			if ('Clearing', account.clearing_account) not in present:
				frappe.throw(_('Missing clearing component for {0}.').format(account.clearing_account))

			if ('Settlement', account.settlement_account) not in present:
				frappe.throw(_('Missing settlement component for {0}.').format(account.settlement_account))

	def _validate_component_calculation_methods(self) -> None:
		allowed_methods = {
			'Clearing': ('Automatic',),
			'Settlement': ('Automatic', 'Manual'),
			'Adjustment': ('Manual',),
			'Component': ('Manual', 'Percentage', 'Fixed Amount'),
			'Manual': ('Manual', 'Percentage', 'Fixed Amount'),
		}
		for component in self.components:
			if component.calculation_method not in allowed_methods.get(component.type, ()):
				frappe.throw(_('Invalid Option'), title=_('Calculation Method'))

	def _calculate_clearing_components(self):
		references_by_mode = {}

		for reference in self.references:
			references_by_mode.setdefault(reference.mode_of_payment, []).append(reference)

		for account in self.accounts:
			references = references_by_mode.get(account.mode_of_payment, [])

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

	def _calculate_percentage_components(self):
		clearing_accounts = {account.clearing_account: account for account in self.accounts}

		for component in self.components:
			if component.type not in ('Component', 'Manual') or component.calculation_method != 'Percentage':
				continue

			account = clearing_accounts.get(component.apply_to)
			if not account:
				frappe.throw(_('Row {0}: Apply To does not belong to this settlement.').format(component.idx))

			if component.account_currency != account.clearing_account_currency:
				frappe.throw(
					_('Account {0} is invalid. Account Currency must be {1}').format(
						component.account, account.clearing_account_currency
					)
				)

			if component.add_deduct_tax not in ('Add', 'Deduct'):
				frappe.throw(_('Invalid Option'), title=_('Add or Deduct'))

			# Use gross collections in account currency; base rounding happens with the other components.
			amount = account.clearing_amount * (component.rate or 0) / 100
			component.debit_in_account_currency = amount if component.add_deduct_tax == 'Deduct' else 0
			component.credit_in_account_currency = amount if component.add_deduct_tax == 'Add' else 0

	def _set_component_exchange_rates(self):
		if not self.posting_date:
			return

		company_currency = frappe.get_cached_value('Company', self.company, 'default_currency')
		rates = {}

		for component in self.components:
			if component.account_currency == company_currency:
				component.exchange_rate = 1
			elif component.type == 'Clearing':  # Preserve the aggregate rate of the original collections.
				component.exchange_rate = (
					component.credit / component.credit_in_account_currency if component.credit_in_account_currency else 0
				)
			elif not component.exchange_rate:
				if component.account_currency not in rates:
					rates[component.account_currency] = get_exchange_rate(
						component.account_currency, company_currency, self.posting_date
					)
				component.exchange_rate = rates[component.account_currency]

			if component.type == 'Clearing':
				continue  # Keep the source base amounts instead of recalculating historical collections.

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
				if component.calculation_method == 'Manual':
					previous = settlement_components.get(component.account)
					if previous and previous.calculation_method == 'Manual':
						frappe.throw(
							_('Duplicate {0} found in the table').format(component.account),
							title=f'{_("Settlement")} ({_("Manual")})',
						)
					settlement_components[component.account] = component
				else:
					settlement_components.setdefault(component.account, component)

		for account in self.accounts:
			clearing_accounts[account.clearing_account] = account.settlement_account
			settlement = settlement_components.get(account.settlement_account)

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
			elif component.calculation_method == 'Automatic':
				balance = settlements[component.account]
				component.debit_in_account_currency = max(balance, 0)
				component.credit_in_account_currency = max(-balance, 0)
			# Base amounts may leave an exchange difference; do not alter the cash balance to hide it.
			self._calculate_component_base_amounts(component)
