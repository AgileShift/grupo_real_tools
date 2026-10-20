import frappe
from frappe.query_builder import Case, Tuple
from frappe.query_builder.custom import ConstantColumn


def _get_payment_entry_references(company: str, accounts, from_date, to_date):
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
	)

	return references.run(as_dict=True)


def _get_sales_invoice_payment_references(company: str, accounts, from_date, to_date):
	account = frappe.qb.DocType('Account')
	sales_invoice = frappe.qb.DocType('Sales Invoice')
	sales_invoice_payment = frappe.qb.DocType('Sales Invoice Payment')
	company_currency = frappe.get_cached_value('Company', company, 'default_currency')

	references = (
		frappe.qb.from_(sales_invoice)
		.inner_join(sales_invoice_payment).on(
			(sales_invoice_payment.parent == sales_invoice.name)
			& (sales_invoice_payment.parenttype == 'Sales Invoice')
		)
		.inner_join(account).on(sales_invoice_payment.account == account.name)
		.select(
			ConstantColumn('Sales Invoice').as_('reference_doctype'),
			sales_invoice.name.as_('reference_name'),
			sales_invoice_payment.name.as_('reference_row_name'),
			sales_invoice.posting_date,
			ConstantColumn('Customer').as_('party_type'),
			sales_invoice.customer.as_('party'),
			sales_invoice.customer_name.as_('party_name'),
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
	)

	return references.run(as_dict=True)
