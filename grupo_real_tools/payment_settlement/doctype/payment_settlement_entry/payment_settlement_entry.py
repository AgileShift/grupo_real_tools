import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class PaymentSettlementEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from grupo_real_tools.payment_settlement.doctype.payment_settlement_entry_component.payment_settlement_entry_component import PaymentSettlementEntryComponent

		amended_from: DF.Link | None
		bank_account: DF.Link
		clearing_account: DF.Link
		company: DF.Link
		components: DF.Table[PaymentSettlementEntryComponent]
		from_date: DF.Datetime
		mode_of_payment: DF.Link
		payment_settlement_template: DF.Link
		posting_date: DF.Date
		settlement_account: DF.Link
		to_date: DF.Datetime
	# end: auto-generated types

	def validate(self):
		self._validate_date_range()

	def _validate_date_range(self):
		if self.from_date and self.to_date and getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_('From Date cannot be later than To Date.'))

	@frappe.whitelist()
	def fetch_payment_sources(self):
		self._validate_fetch_filters()

		return get_payment_sources(
			company=self.company,
			mode_of_payment=self.mode_of_payment,
			from_date=self.from_date,
			to_date=self.to_date,
		)

	def _validate_fetch_filters(self):
		required_fields = {
			'company': _('Company'),
			'mode_of_payment': _('Mode of Payment'),
			'from_date': _('From Date'),
			'to_date': _('To Date'),
		}
		missing = [label for fieldname, label in required_fields.items() if not self.get(fieldname)]

		if missing:
			frappe.throw(_('Please set {0} before fetching payments.').format(', '.join(missing)))


@frappe.whitelist()
def get_payment_sources(company: str, mode_of_payment: str, from_date: str, to_date: str):
	from_date_only, to_date_only = _validate_fetch_filters(company, mode_of_payment, from_date, to_date)

	payment_entries = frappe.get_all(
		'Payment Entry',
		filters={
			'docstatus': 1,
			'company': company,
			'mode_of_payment': mode_of_payment,
			'payment_type': 'Receive',
			'posting_date': ['between', [from_date_only, to_date_only]],
		},
		fields=[
			'name',
			'posting_date',
			'party_type',
			'party',
			'party_name',
			'paid_from',
			'paid_to',
			'received_amount',
			'base_received_amount',
			'reference_no',
		],
		order_by='posting_date asc, name asc',
	)

	sales_invoice_payments = frappe.db.sql(
		"""
		select
			sip.name as sales_invoice_payment_row,
			sip.parent as sales_invoice,
			si.posting_date,
			si.customer,
			si.customer_name,
			sip.amount,
			sip.base_amount,
			sip.reference_no
		from `tabSales Invoice Payment` sip
		inner join `tabSales Invoice` si on si.name = sip.parent
		where
			si.docstatus = 1
			and ifnull(si.is_return, 0) = 0
			and si.company = %(company)s
			and sip.mode_of_payment = %(mode_of_payment)s
			and si.posting_date between %(from_date)s and %(to_date)s
		order by si.posting_date asc, sip.parent asc, sip.idx asc
		""",
		{
			'company': company,
			'mode_of_payment': mode_of_payment,
			'from_date': from_date_only,
			'to_date': to_date_only,
		},
		as_dict=True,
	)

	payment_entry_total = sum(flt(d.base_received_amount) for d in payment_entries)
	sales_invoice_payment_total = sum(flt(d.base_amount) for d in sales_invoice_payments)

	return {
		'filters': {
			'company': company,
			'mode_of_payment': mode_of_payment,
			'from_date': str(from_date_only),
			'to_date': str(to_date_only),
		},
		'payment_entries': payment_entries,
		'sales_invoice_payments': sales_invoice_payments,
		'totals': {
			'payment_entries_count': len(payment_entries),
			'sales_invoice_payments_count': len(sales_invoice_payments),
			'payment_entries_base_amount': payment_entry_total,
			'sales_invoice_payments_base_amount': sales_invoice_payment_total,
			'base_amount': payment_entry_total + sales_invoice_payment_total,
		},
	}


def _validate_fetch_filters(company: str, mode_of_payment: str, from_date: str, to_date: str):
	if not company:
		frappe.throw(_('Company is required.'))
	if not mode_of_payment:
		frappe.throw(_('Mode of Payment is required.'))
	if not from_date:
		frappe.throw(_('From Date is required.'))
	if not to_date:
		frappe.throw(_('To Date is required.'))

	from_date_only = getdate(from_date)
	to_date_only = getdate(to_date)

	if from_date_only > to_date_only:
		frappe.throw(_('From Date cannot be later than To Date.'))

	return from_date_only, to_date_only
