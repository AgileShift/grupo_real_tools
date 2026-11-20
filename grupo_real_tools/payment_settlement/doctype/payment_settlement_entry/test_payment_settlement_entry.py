"""Settlement regression tests using real Frappe documents and accounting lifecycles."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, getdate

from erpnext.accounts.doctype.account.test_account import create_account


EXTRA_TEST_RECORD_DEPENDENCIES = ['Company', 'Customer', 'Fiscal Year']
IGNORE_TEST_RECORD_DEPENDENCIES = ['Payment Settlement Template', 'Journal Entry']


class IntegrationTestPaymentSettlementEntry(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.db.rollback)
		self.company = '_Test Company'
		self.currency = frappe.get_cached_value('Company', self.company, 'default_currency')
		self.posting_date = '2013-01-15'
		self.suffix = frappe.generate_hash(length=8)
		self.serial = 0
		self.foreign_currency = 'USD' if self.currency != 'USD' else 'EUR'
		self.destination = self.make_account('Destination')
		self.manual_account = self.make_account('Manual Bank')
		self.other_account = self.make_account('Other Bank')
		self.destination_bank = self.make_bank_account(self.destination)
		self.manual_bank = self.make_bank_account(self.manual_account)
		self.other_bank = self.make_bank_account(self.other_account)
		self.source = self.make_source('POS', destination=self.destination, bank_account=self.destination_bank)
		self.clearing = self.source.clearing_account

	def make_account(self, label, currency=None, expense=False):
		self.serial += 1
		return create_account(
			account_name=f'_Test {label} {self.suffix} {self.serial}', company=self.company,
			parent_account='Indirect Expenses - _TC' if expense else 'Bank Accounts - _TC',
			account_type=None if expense else 'Bank', account_currency=currency or self.currency,
		)

	def make_bank_account(self, account):
		bank = f'_Test Settlement Bank {self.suffix}'
		if not frappe.db.exists('Bank', bank):
			frappe.new_doc('Bank', bank_name=bank).insert()
		return frappe.new_doc(
			'Bank Account', account_name=account, bank=bank,
			company=self.company, account=account, is_company_account=1,
		).insert().name

	def make_source(self, label, currency=None, destination=None, bank_account=None):
		currency = currency or self.currency
		clearing = self.make_account(f'{label} Clearing', currency)
		if not destination:
			destination = self.make_account(f'{label} Destination', currency)
			bank_account = self.make_bank_account(destination)
		mode = frappe.new_doc(
			'Mode of Payment', mode_of_payment=f'_Test {label} {self.suffix} {self.serial}', type='Bank',
			accounts=[{'company': self.company, 'default_account': clearing}],
		).insert()
		return frappe._dict(
			mode_of_payment=mode.name, clearing_account=clearing, clearing_account_currency=currency,
			settlement_account=destination,
			settlement_account_currency=frappe.get_cached_value('Account', destination, 'account_currency'),
			bank_account=bank_account, charge_account=self.make_account(f'{label} Charge', currency, expense=True),
		)

	def make_payment(self, source, amount, rate):
		# Supply rates before validation; the core test helper would fetch live FX before accepting overrides.
		payment = frappe.new_doc(
			'Payment Entry', company=self.company, posting_date=self.posting_date, payment_type='Receive',
			party_type='Customer', party='_Test Customer', mode_of_payment=source.mode_of_payment,
			paid_from='Debtors - _TC', paid_to=source.clearing_account,
			paid_from_account_currency=self.currency, paid_to_account_currency=source.clearing_account_currency,
			source_exchange_rate=1, target_exchange_rate=rate, paid_amount=amount * rate, received_amount=amount,
			reference_no=f'_Test {frappe.generate_hash(length=8)}', reference_date=self.posting_date,
		)
		payment.insert().submit()
		return payment

	def make_sales_invoice(self, payments, rate):
		invoice = frappe.new_doc(
			'Sales Invoice', company=self.company, customer='_Test Customer',
			posting_date=self.posting_date, due_date=self.posting_date, set_posting_time=1,
			currency=self.foreign_currency, conversion_rate=rate, plc_conversion_rate=1,
			is_pos=1, pos_profile='', debit_to='Debtors - _TC',
			items=[{
				'item_name': 'Settlement test service', 'description': 'Settlement test service',
				'qty': 1, 'rate': sum(amount for _, amount in payments),
				'uom': 'Nos', 'stock_uom': 'Nos', 'conversion_factor': 1,
				'income_account': 'Sales - _TC', 'cost_center': 'Main - _TC',
			}],
			payments=[{
				'mode_of_payment': source.mode_of_payment, 'account': source.clearing_account, 'amount': amount,
			} for source, amount in payments],
		)
		invoice.insert().submit()
		return invoice

	def make_entry(self, manual_account=None, *, amount=1000, percentage=False, sources=None, rate=0.02):
		sources = sources or [(self.source, amount, 1)]
		payments = [self.make_payment(source, value, receipt_rate) for source, value, receipt_rate in sources]
		template = frappe.new_doc('Payment Settlement Template', company=self.company, voucher_type='Journal Entry')
		template.name = f'_Test Settlement {frappe.generate_hash(length=8)}'
		for source, _, _ in sources:
			template.append('accounts', {
				field: source[field] for field in (
					'mode_of_payment', 'clearing_account', 'clearing_account_currency', 'settlement_account',
					'settlement_account_currency', 'bank_account',
				)
			})
			component = template.append('components', {
				'account': source.charge_account, 'account_currency': source.clearing_account_currency,
				'calculation_method': 'Percentage' if percentage else 'Manual',
				'apply_to': source.clearing_account,
			})
			if percentage:
				component.add_deduct_tax = 'Deduct'
				component.rate = 5.5
		template.insert()
		entry = frappe.new_doc(
			'Payment Settlement Entry', company=self.company, template=template.name,
			naming_series='PS-.YYYY.-.#####', posting_date=self.posting_date,
			from_date=self.posting_date, to_date=self.posting_date + ' 23:59:59',
		)
		entry.fetch_template_data()
		for row in entry.components:
			if row.account_currency != self.currency:
				row.exchange_rate = rate
		entry.fetch_references()
		self.assertCountEqual([row.reference_name for row in entry.references], [payment.name for payment in payments])
		if manual_account:
			entry.append('components', {
				'type': 'Manual', 'calculation_method': 'Manual', 'account': manual_account,
				'account_currency': self.currency, 'debit_in_account_currency': 100,
				'apply_to': self.clearing, 'user_remark': 'Additional bank destination',
			})
		return entry.insert()

	@staticmethod
	def get_component(entry, row_type, account=None):
		return next(row for row in entry.components if row.type == row_type and (not account or row.account == account))

	def add_manual_component(self, entry, account, **values):
		return entry.append('components', {
			'type': 'Manual', 'calculation_method': 'Manual', 'account': account,
			'account_currency': frappe.get_cached_value('Account', account, 'account_currency'), **values,
		})

	def assert_journal_round_trip(self, entry):
		entry.submit()
		entry.reload()
		journal = frappe.get_doc('Journal Entry', entry.journal_entry)
		self.assertEqual(journal.docstatus, 1)
		components = [row for row in entry.components if row.debit or row.credit]
		self.assertEqual(len(journal.accounts), len(components))
		expected = {}
		for component, row in zip(components, journal.accounts, strict=True):
			self.assertEqual(row.account, component.account)
			self.assertEqual(row.account_currency, component.account_currency)
			self.assertEqual((row.debit, row.credit), (component.debit, component.credit))
			self.assertEqual(
				(row.debit_in_account_currency, row.credit_in_account_currency),
				(component.debit_in_account_currency, component.credit_in_account_currency),
			)
			self.assertEqual(row.bank_account or None, component.bank_account or None)
			self.assertEqual(row.user_remark or None, component.user_remark or None)
			expected[row.account] = expected.get(row.account, 0) + row.debit - row.credit
		ledger = frappe.get_all('GL Entry', {
			'voucher_type': 'Journal Entry', 'voucher_no': journal.name, 'is_cancelled': 0,
		}, ['account', 'debit', 'credit'])
		self.assertTrue(ledger)
		actual = {}
		for row in ledger:
			actual[row.account] = actual.get(row.account, 0) + row.debit - row.credit
		precision = entry.precision('total_debit')
		self.assertEqual(
			{account: flt(value, precision) for account, value in actual.items() if flt(value, precision)},
			{account: flt(value, precision) for account, value in expected.items() if flt(value, precision)},
		)
		entry.cancel()
		self.assertEqual(entry.reload().docstatus, 2)
		self.assertEqual(journal.reload().docstatus, 2)
		self.assertFalse(frappe.db.exists('GL Entry', {
			'voucher_type': 'Journal Entry', 'voucher_no': journal.name, 'is_cancelled': 0,
		}))
		return journal

	def test_manual_bank_reaches_real_journal_and_cancel(self):
		entry = self.make_entry(self.manual_account)
		self.assertEqual(entry.components[-1].bank_account, self.manual_bank)
		self.assertIsNone(entry.components[0].bank_account)
		self.assertEqual(entry.accounts[0].bank_account, self.destination_bank)
		self.assertEqual(entry.difference, 0)
		journal = self.assert_journal_round_trip(entry)
		rows = {row.account: row for row in journal.accounts}
		self.assertEqual(rows[self.manual_account].bank_account, self.manual_bank)
		self.assertEqual(rows[self.manual_account].user_remark, 'Additional bank destination')
		self.assertEqual(rows[self.destination].bank_account, self.destination_bank)
		self.assertEqual(rows[self.destination].debit_in_account_currency, 900)
		self.assertFalse(rows[self.clearing].bank_account)

	def test_bank_entry_uses_reference_number_and_posting_date(self):
		entry = self.make_entry()
		template = frappe.get_doc('Payment Settlement Template', entry.template)
		template.voucher_type = 'Bank Entry'
		template.save()
		entry.fetch_template_data()
		entry.cheque_no = 'TEST-DEPOSIT'
		entry.save()

		journal = self.assert_journal_round_trip(entry)
		self.assertEqual(journal.voucher_type, 'Bank Entry')
		self.assertEqual(journal.cheque_no, entry.cheque_no)
		self.assertEqual(getdate(journal.cheque_date), getdate(entry.posting_date))

	def test_general_remark_is_copied_to_journal(self):
		entry = self.make_entry()
		entry.remark = 'Deposit details\nSecond line'
		entry.save()
		journal = self.assert_journal_round_trip(entry)
		self.assertEqual(journal.title, f'{entry.template} · {entry.name}')
		self.assertTrue(journal.custom_remark)
		self.assertEqual(journal.remark, entry.remark)

	def test_empty_general_remark_uses_erpnext_default(self):
		entry = self.make_entry()
		journal = self.assert_journal_round_trip(entry)
		self.assertEqual(journal.title, f'{entry.template} · {entry.name}')
		self.assertFalse(journal.custom_remark)

	def test_account_change_and_bank_typed_clearing_without_link(self):
		entry = self.make_entry(self.manual_account)
		manual = entry.components[-1]
		manual.account = self.other_account
		entry.save()
		self.assertEqual(manual.bank_account, self.other_bank)

		manual.account = None
		entry.calculate()
		self.assertIsNone(manual.bank_account)
		with self.assertRaises(frappe.MandatoryError):
			entry.save()
		entry.reload()
		manual = entry.components[-1]
		manual.account = self.clearing
		entry.save()
		self.assertIsNone(manual.bank_account)
		self.assertEqual(entry.difference, 0)
		journal = self.assert_journal_round_trip(entry)
		self.assertTrue(all(not row.bank_account for row in journal.accounts if row.account == self.clearing))

	def test_percentage_template_copy_and_add_or_deduct(self):
		entry = self.make_entry(percentage=True)
		fee = self.get_component(entry, 'Component')
		self.assertEqual((fee.calculation_method, fee.add_deduct_tax, fee.rate), ('Percentage', 'Deduct', 5.5))
		self.assertEqual(fee.based_on, 'On Gross Amount')
		self.assertEqual((fee.debit_in_account_currency, fee.credit_in_account_currency), (55, 0))
		self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 945)
		self.assertTrue(all(row.calculation_method == 'Automatic' for row in entry.components if row.type != 'Component'))

		template = frappe.get_doc('Payment Settlement Template', entry.template)
		template.components[0].add_deduct_tax = 'Add'
		template.components[0].based_on = 'On Previous Row Total'
		template.save()
		self.assertEqual(self.get_component(entry.reload(), 'Component').add_deduct_tax, 'Deduct')
		self.assertEqual(self.get_component(entry, 'Component').based_on, 'On Gross Amount')
		entry.fetch_template_data()
		entry.fetch_references()
		entry.save()
		fee = self.get_component(entry, 'Component')
		self.assertEqual(fee.based_on, 'On Previous Row Total')
		self.assertEqual((fee.debit_in_account_currency, fee.credit_in_account_currency), (0, 55))
		self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 1055)
		fee.user_remark = 'Percentage copied from the template'
		entry.save()
		self.assert_journal_round_trip(entry)

	def test_percentage_cascade_uses_rounded_configured_charges(self):
		entry = self.make_entry(percentage=True, amount=1000.01)
		entry.append('components', {
			'type': 'Component', 'calculation_method': 'Manual',
			'account': self.make_account('Fixed charge', expense=True), 'account_currency': self.currency,
			'debit_in_account_currency': 0.10,
		})
		retention = entry.append('components', {
			'type': 'Component', 'calculation_method': 'Percentage', 'based_on': 'On Previous Row Total',
			'account': self.make_account('Retention', expense=True), 'account_currency': self.currency,
			'add_deduct_tax': 'Deduct', 'rate': 1.5, 'apply_to': self.clearing,
		})
		self.add_manual_component(entry, self.manual_account, credit_in_account_currency=20, apply_to=self.clearing)
		entry.save()
		self.assertEqual(retention.debit_in_account_currency, 14.17)
		self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 950.74)
		entry.calculate()
		self.assertEqual(retention.debit_in_account_currency, 14.17)
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_percentage_basis_defaults_to_gross_and_rejects_invalid_options(self):
		entry = self.make_entry(percentage=True)
		fee = self.get_component(entry, 'Component')
		fee.based_on = ''
		entry.save()
		self.assertEqual(fee.based_on, 'On Gross Amount')
		self.assertEqual(fee.debit_in_account_currency, 55)
		fee.based_on = 'Invalid'
		with self.assertRaises(frappe.ValidationError):
			entry.save()

	def test_removing_all_references_clears_calculations_but_cannot_be_saved(self):
		entry = self.make_entry(percentage=True)
		entry.set('references', [])
		entry.calculate()
		self.assertEqual(entry.accounts[0].reference_count, 0)
		self.assertTrue(all(not (row.debit or row.credit) for row in entry.components))
		self.assertEqual(self.get_component(entry, 'Clearing').exchange_rate, 1)
		with self.assertRaises(frappe.MandatoryError):
			entry.save()
		self.assertEqual(len(entry.reload().references), 1)

	def test_manual_amounts_are_preserved_and_journal_rejects_both_sides(self):
		entry = self.make_entry(percentage=True)
		fee = self.get_component(entry, 'Component')
		fee.calculation_method = 'Manual'
		fee.debit_in_account_currency, fee.credit_in_account_currency = 60, 10
		entry.save()
		fee = self.get_component(entry.reload(), 'Component')
		self.assertEqual((fee.debit_in_account_currency, fee.credit_in_account_currency), (60, 10))
		self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 950)
		# on_submit runs after the parent write; restore the failed transaction as a request would.
		frappe.db.savepoint('invalid_journal')
		with self.assertRaisesRegex(frappe.ValidationError, 'You cannot credit and debit same account at the same time'):
			entry.submit()
		frappe.db.rollback(save_point='invalid_journal')
		entry.reload()
		self.assertEqual(entry.docstatus, 0)
		self.get_component(entry, 'Component').credit_in_account_currency = 0
		entry.save()
		self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 940)
		self.assert_journal_round_trip(entry)

	def test_foreign_currency_direct_amounts_and_precision_difference(self):
		source = self.make_source('Foreign', currency=self.foreign_currency)
		entry = self.make_entry(percentage=True, sources=[(source, 1000, 0.02731)], rate=0.0273)
		self.assertEqual(self.get_component(entry, 'Component').debit_in_account_currency, 55)
		self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 945)
		self.assertEqual(entry.difference, -0.01)
		with self.assertRaises(frappe.ValidationError):
			entry.submit()
		entry.reload()
		entry.make_difference('Round Off')
		entry.save()
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_foreign_invoice_payment_uses_base_amount_for_company_currency_clearing(self):
		entry = self.make_entry()
		invoice = self.make_sales_invoice([(self.source, 1000)], rate=0.02)
		entry.fetch_references()
		entry.save()
		reference = next(row for row in entry.references if row.reference_name == invoice.name)
		self.assertEqual(
			(reference.account, reference.currency, reference.amount, reference.base_amount, reference.exchange_rate),
			(self.clearing, self.currency, 20, 20, 1),
		)
		self.assertEqual(entry.accounts[0].clearing_amount, 1020)
		clearing = self.get_component(entry, 'Clearing')
		self.assertEqual(
			(clearing.credit_in_account_currency, clearing.credit, clearing.exchange_rate), (1020, 1020, 1)
		)
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_foreign_invoice_split_between_company_and_foreign_currency_clearing(self):
		foreign = self.make_source('Foreign', currency=self.foreign_currency)
		entry = self.make_entry(sources=[(self.source, 40, 1), (foreign, 1000, 0.02)])
		invoice = self.make_sales_invoice([(self.source, 500), (foreign, 500)], rate=0.02)
		entry.fetch_references()
		entry.save()
		self.assertEqual(len([row for row in entry.references if row.reference_name == invoice.name]), 2)
		invoice_references = {
			row.account: row for row in entry.references if row.reference_name == invoice.name
		}
		company_reference = invoice_references[self.clearing]
		foreign_reference = invoice_references[foreign.clearing_account]
		self.assertEqual(
			(company_reference.currency, company_reference.amount, company_reference.exchange_rate),
			(self.currency, 10, 1),
		)
		self.assertEqual(
			(foreign_reference.currency, foreign_reference.amount, foreign_reference.exchange_rate),
			(self.foreign_currency, 500, 0.02),
		)
		company_clearing = self.get_component(entry, 'Clearing', self.clearing)
		foreign_clearing = self.get_component(entry, 'Clearing', foreign.clearing_account)
		self.assertEqual((company_clearing.credit_in_account_currency, company_clearing.exchange_rate), (50, 1))
		self.assertEqual((foreign_clearing.credit_in_account_currency, foreign_clearing.credit), (1500, 30))
		self.assertEqual(foreign_clearing.exchange_rate, 0.02)
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_invoice_payment_rows_in_the_same_account_keep_their_identity(self):
		entry = self.make_entry()
		invoice = self.make_sales_invoice([(self.source, 400), (self.source, 600)], rate=0.02)
		entry.fetch_references()
		entry.save()
		references = [row for row in entry.references if row.reference_name == invoice.name]
		self.assertEqual(len(references), 2)
		self.assertEqual(len({row.reference_row_name for row in references}), 2)
		self.assertEqual([row.amount for row in references], [8, 12])
		self.assertTrue(all(row.account == self.clearing and row.currency == self.currency for row in references))
		self.assertTrue(all(row.exchange_rate == 1 for row in references))
		self.assertEqual(entry.accounts[0].clearing_amount, 1020)
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_percentage_component_must_use_the_source_currency(self):
		source = self.make_source('Foreign', currency=self.foreign_currency)
		entry = self.make_entry(percentage=True, sources=[(source, 1000, 0.02)])
		fee = self.get_component(entry, 'Component')
		fee.account, fee.account_currency = self.source.charge_account, self.currency
		with self.assertRaises(frappe.ValidationError):
			entry.save()

	def test_percentage_apply_to_and_direction_are_validated_on_save(self):
		entry = self.make_entry(percentage=True)
		for fieldname, value in (
			('apply_to', None), ('apply_to', self.other_account),
			('add_deduct_tax', None), ('add_deduct_tax', 'Other'),
		):
			with self.subTest(fieldname=fieldname, value=value):
				self.get_component(entry.reload(), 'Component').set(fieldname, value)
				with self.assertRaises(frappe.ValidationError):
					entry.save()

	def test_multiple_sources_share_a_bank_without_duplicating_the_residual(self):
		other = self.make_source('Other POS', destination=self.destination, bank_account=self.destination_bank)
		entry = self.make_entry(percentage=True, sources=[(self.source, 1000, 1), (other, 2000, 1)])
		fees = [row.debit_in_account_currency for row in entry.components if row.type == 'Component']
		self.assertEqual(fees, [55, 110])
		settlements = entry.get('components', {'type': 'Settlement'})
		self.assertEqual([row.debit_in_account_currency for row in settlements], [2835, 0])
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_mixed_currencies_and_multiple_destinations(self):
		foreign = self.make_source('Foreign', currency=self.foreign_currency)
		entry = self.make_entry(percentage=True, sources=[(self.source, 40, 1), (foreign, 1000, 0.02)])
		self.assertEqual(self.get_component(entry, 'Settlement', self.destination).debit_in_account_currency, 37.8)
		self.assertEqual(self.get_component(entry, 'Settlement', foreign.settlement_account).debit_in_account_currency, 945)
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_foreign_manual_component_converts_through_company_currency(self):
		entry = self.make_entry(percentage=True)
		expense = self.make_account('Foreign Expense', self.foreign_currency, expense=True)
		self.add_manual_component(
			entry, expense, debit_in_account_currency=100, exchange_rate=0.02, apply_to=self.clearing,
		)
		entry.save()
		self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 943)
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_expenses_and_manual_funding_produce_credit_and_debit_residuals(self):
		entry = self.make_entry(percentage=True)
		self.add_manual_component(entry, self.source.charge_account, debit_in_account_currency=1100, apply_to=self.clearing)
		entry.save()
		self.assertEqual(self.get_component(entry, 'Settlement').credit_in_account_currency, 155)
		funded = frappe.copy_doc(entry).insert()
		self.assert_journal_round_trip(entry)
		self.add_manual_component(funded, self.manual_account, credit_in_account_currency=300, apply_to=self.clearing)
		funded.save()
		settlement = self.get_component(funded, 'Settlement')
		self.assertEqual((settlement.debit_in_account_currency, settlement.credit_in_account_currency), (145, 0))
		self.assert_journal_round_trip(funded)

	def test_manual_settlement_is_saved_but_a_difference_blocks_submit(self):
		entry = self.make_entry(percentage=True)
		settlement = self.get_component(entry, 'Settlement')
		settlement.calculation_method = 'Manual'
		settlement.debit_in_account_currency = 900
		entry.save()
		self.assertEqual(self.get_component(entry.reload(), 'Settlement').debit_in_account_currency, 900)
		self.assertEqual(entry.difference, -45)
		with self.assertRaises(frappe.ValidationError):
			entry.submit()
		self.assertEqual(entry.reload().docstatus, 0)
		self.assertFalse(entry.journal_entry)

	def test_automatic_settlement_replaces_entered_amounts(self):
		entry = self.make_entry(percentage=True)
		self.get_component(entry, 'Settlement').debit_in_account_currency = 900
		entry.save()
		self.assertEqual(self.get_component(entry.reload(), 'Settlement').debit_in_account_currency, 945)
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_switching_a_manual_credit_settlement_back_to_automatic(self):
		entry = self.make_entry(percentage=True)
		settlement = self.get_component(entry, 'Settlement')
		settlement.calculation_method = 'Manual'
		settlement.debit_in_account_currency = 0
		settlement.credit_in_account_currency = 50
		entry.save()
		settlement = self.get_component(entry.reload(), 'Settlement')
		self.assertEqual((settlement.debit_in_account_currency, settlement.credit_in_account_currency), (0, 50))
		settlement.calculation_method = 'Automatic'
		entry.save()
		settlement = self.get_component(entry.reload(), 'Settlement')
		self.assertEqual((settlement.debit_in_account_currency, settlement.credit_in_account_currency), (945, 0))
		self.assert_journal_round_trip(entry)

	def test_manual_foreign_settlement_recalculates_only_company_amounts(self):
		source = self.make_source('Foreign', currency=self.foreign_currency)
		entry = self.make_entry(percentage=True, sources=[(source, 1000, 0.02)])
		settlement = self.get_component(entry, 'Settlement')
		settlement.calculation_method = 'Manual'
		settlement.debit_in_account_currency = 0
		settlement.credit_in_account_currency = 50
		entry.save()
		settlement = self.get_component(entry.reload(), 'Settlement')
		self.assertEqual((settlement.debit_in_account_currency, settlement.credit_in_account_currency), (0, 50))
		self.assertEqual((settlement.debit, settlement.credit), (0, 1))

	def test_manual_settlement_takes_precedence_regardless_of_row_order(self):
		entry = self.make_entry(percentage=True)
		for manual_first in (True, False):
			with self.subTest(manual_first=manual_first):
				manual = entry.append('components', {
					'type': 'Settlement', 'account': self.destination, 'account_currency': self.currency,
					'calculation_method': 'Manual', 'debit_in_account_currency': 900,
				})
				if manual_first:
					entry.set('components', [manual, *entry.components[:-1]])
				entry.save()
				automatic = next(row for row in entry.components if row.type == 'Settlement' and row != manual)
				self.assertEqual((automatic.debit_in_account_currency, automatic.credit_in_account_currency), (0, 0))
				self.assertEqual(manual.debit_in_account_currency, 900)
				self.assertEqual(entry.difference, -45)
				entry.remove(manual)
				entry.save()
		self.assert_journal_round_trip(entry)

	def test_duplicate_automatic_settlement_rows_are_zeroed(self):
		entry = self.make_entry(percentage=True)
		duplicate = entry.append('components', {
			'type': 'Settlement', 'account': self.destination, 'account_currency': self.currency,
			'calculation_method': 'Automatic', 'credit_in_account_currency': 10,
		})
		entry.save()
		self.assertEqual((duplicate.debit_in_account_currency, duplicate.credit_in_account_currency), (0, 0))
		self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 945)
		self.assert_journal_round_trip(entry)

	def test_duplicate_manual_settlements_are_rejected_on_save(self):
		entry = self.make_entry()
		self.get_component(entry, 'Settlement').calculation_method = 'Manual'
		entry.append('components', {
			'type': 'Settlement', 'account': self.destination, 'account_currency': self.currency,
			'calculation_method': 'Manual',
		})
		with self.assertRaises(frappe.ValidationError):
			entry.save()

	def test_calculation_methods_are_validated_on_save(self):
		entry = self.make_entry()
		for row_type, method in (
			('Clearing', 'Manual'), ('Clearing', 'Percentage'),
			('Settlement', 'Percentage'), ('Settlement', 'Fixed Amount'),
			('Adjustment', 'Automatic'), ('Adjustment', 'Percentage'),
			('Component', 'Automatic'), ('Manual', 'Automatic'),
		):
			with self.subTest(row_type=row_type, method=method):
				entry.reload().append('components', {
					'type': row_type, 'calculation_method': method, 'account': self.manual_account,
					'account_currency': self.currency,
				})
				with self.assertRaises(frappe.ValidationError):
					entry.save()

	def test_company_difference_accounts_create_manual_adjustments(self):
		base = self.make_entry(percentage=True)
		settlement = self.get_component(base, 'Settlement')
		settlement.calculation_method, settlement.debit_in_account_currency = 'Manual', 900
		base.save()
		company = frappe.get_cached_doc('Company', self.company)
		for adjustment_type, fieldname in (
			('Round Off', 'round_off_account'), ('Exchange Gain Or Loss', 'exchange_gain_loss_account'),
			('Write Off', 'write_off_account'),
		):
			with self.subTest(adjustment_type=adjustment_type):
				self.assertTrue(company.get(fieldname), f'The core Company fixture needs {fieldname}')
				entry = frappe.copy_doc(base).insert()
				entry.make_difference(adjustment_type)
				entry.save()
				adjustment = self.get_component(entry.reload(), 'Adjustment')
				self.assertEqual((adjustment.account, adjustment.calculation_method), (company.get(fieldname), 'Manual'))
				self.assertEqual(adjustment.debit_in_account_currency, 45)
				self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 900)
				self.assertEqual(entry.difference, 0)
				self.assert_journal_round_trip(entry)

	def test_percentage_uses_native_field_precision(self):
		entry = self.make_entry(percentage=True, amount=1000.01)
		self.assertEqual(self.get_component(entry, 'Component').debit_in_account_currency, 55)
		self.assertEqual(self.get_component(entry, 'Settlement').debit_in_account_currency, 945.01)
		self.assertEqual(entry.difference, 0)
		self.assert_journal_round_trip(entry)

	def test_missing_structural_components_cannot_be_saved(self):
		entry = self.make_entry()
		for row_type in ('Clearing', 'Settlement'):
			with self.subTest(row_type=row_type):
				entry.reload().remove(self.get_component(entry, row_type))
				with self.assertRaises(frappe.ValidationError):
					entry.save()

	def test_previously_settled_references_are_rejected_at_submit(self):
		entry = self.make_entry()
		other = frappe.copy_doc(entry).insert()
		entry.submit()
		with self.assertRaises(frappe.ValidationError):
			other.submit()
		other.reload().fetch_references()
		self.assertFalse(other.references)
		entry.cancel()
		self.assertEqual(frappe.get_doc('Journal Entry', entry.journal_entry).docstatus, 2)

	def test_cancelled_source_is_rejected_by_native_link_validation(self):
		entry = self.make_entry()
		frappe.get_doc('Payment Entry', entry.references[0].reference_name).cancel()
		with self.assertRaises(frappe.CancelledLinkError):
			entry.submit()

	def test_non_bank_destination_does_not_require_a_bank_account(self):
		destination = create_account(
			account_name=f'_Test Clearing Destination {self.suffix}', company=self.company,
			parent_account='Current Assets - _TC', account_currency=self.currency,
		)
		source = self.make_source('Non-bank', destination=destination)
		entry = self.make_entry(sources=[(source, 1000, 1)])
		self.assertFalse(self.get_component(entry, 'Settlement').bank_account)
		self.assert_journal_round_trip(entry)
