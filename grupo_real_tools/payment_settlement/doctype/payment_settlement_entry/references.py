import frappe
from frappe.query_builder import Case, Tuple
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import getdate


def get_references(company: str, accounts: list, from_date, to_date) -> list:
	""" Return eligible collection events that are not in a submitted Settlement. """
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	accounts = [(account.mode_of_payment, account.clearing_account) for account in accounts]

	references = (
		_get_payment_entry_references(company, accounts, from_date, to_date) +
		_get_sales_invoice_payment_references(company, accounts, from_date, to_date)
	) if accounts else []

	candidate_names = {reference.reference_name for reference in references}
	settled = get_settled_references(candidate_names)

	return [
		row for row in references
		if (row.reference_doctype, row.reference_name, row.reference_row_name) not in settled
	]


def get_settled_references(candidate_names: set[str]) -> dict:
	""" Map settled identities to their Settlement, querying only matching candidate documents. """
	if not candidate_names:
		return {}

	reference = frappe.qb.DocType('Payment Settlement Entry Reference')
	references = (
		frappe.qb.from_(reference)
		.select(
			reference.reference_doctype, reference.reference_name, reference.reference_row_name, reference.parent,
		).where(
			(reference.docstatus == 1)
			& (reference.parenttype == 'Payment Settlement Entry')
			& reference.reference_name.isin(candidate_names)
		)
	)

	# noinspection PyCallingNonCallable
	return {
		(reference_doctype, reference_name, reference_row_name or ''): parent
		for reference_doctype, reference_name, reference_row_name, parent in references.run()
	}


def _get_payment_entry_references(company: str, accounts: list, from_date, to_date) -> list:
	payment_entry = frappe.qb.DocType('Payment Entry')

	# noinspection PyCallingNonCallable
	return (
		frappe.qb.from_(payment_entry)
		.select(
			ConstantColumn('Payment Entry').as_('reference_doctype'),
			payment_entry.name.as_('reference_name'), ConstantColumn('').as_('reference_row_name'),
			payment_entry.posting_date,
			payment_entry.party_type, payment_entry.party, payment_entry.party_name,
			payment_entry.mode_of_payment,
			payment_entry.paid_to.as_('account'), payment_entry.paid_to_account_currency.as_('currency'),
			payment_entry.target_exchange_rate.as_('exchange_rate'),
			payment_entry.received_amount.as_('amount'),
			payment_entry.base_received_amount.as_('base_amount'),
			payment_entry.reference_no,
		).where(
			(payment_entry.docstatus == 1)
			& (payment_entry.company == company)
			& (payment_entry.payment_type == 'Receive')
			& (Tuple(payment_entry.mode_of_payment, payment_entry.paid_to).isin(accounts))
			& (payment_entry.posting_date.between(from_date, to_date))
		).orderby(payment_entry.mode_of_payment, payment_entry.posting_date)
	).run(as_dict=True)


def _get_sales_invoice_payment_references(company: str, accounts: list, from_date, to_date) -> list:
	account = frappe.qb.DocType('Account')
	sales_invoice = frappe.qb.DocType('Sales Invoice')
	sales_invoice_payment = frappe.qb.DocType('Sales Invoice Payment')
	company_currency = frappe.get_cached_value('Company', company, 'default_currency')

	# noinspection PyCallingNonCallable
	return (
		frappe.qb.from_(sales_invoice)
		.inner_join(sales_invoice_payment).on(
			(sales_invoice_payment.parent == sales_invoice.name)
			& (sales_invoice_payment.parenttype == 'Sales Invoice')
		)
		.inner_join(account).on(sales_invoice_payment.account == account.name)
		.select(
			ConstantColumn('Sales Invoice').as_('reference_doctype'),
			sales_invoice.name.as_('reference_name'), sales_invoice_payment.name.as_('reference_row_name'),
			sales_invoice.posting_date,
			ConstantColumn('Customer').as_('party_type'),
			sales_invoice.customer.as_('party'), sales_invoice.customer_name.as_('party_name'),
			sales_invoice_payment.mode_of_payment,
			sales_invoice_payment.account, account.account_currency.as_('currency'),

			# Invoice payments use invoice currency; normalize amounts and rates to the receiving account currency.
			Case().when(account.account_currency == company_currency, 1)
			.else_(sales_invoice.conversion_rate).as_('exchange_rate'),
			Case().when(account.account_currency == company_currency, sales_invoice_payment.base_amount)
			.else_(sales_invoice_payment.amount).as_('amount'),

			sales_invoice_payment.base_amount,
			sales_invoice_payment.reference_no,
		).where(
			(sales_invoice.docstatus == 1)
			& (sales_invoice.is_return == 0)
			& (sales_invoice.company == company)
			& (Tuple(sales_invoice_payment.mode_of_payment, sales_invoice_payment.account).isin(accounts))
			& (sales_invoice.posting_date.between(from_date, to_date))
		).orderby(
			sales_invoice_payment.mode_of_payment, sales_invoice.posting_date,
			sales_invoice.name, sales_invoice_payment.idx
		)
	).run(as_dict=True)
