"""Replace the legacy Override flag with calculation methods in every Entry state."""

import frappe
from frappe.query_builder import Case


def execute():
	doctype = 'Payment Settlement Entry Component'
	if not frappe.db.table_exists(doctype):
		return

	# A new empty table needs no migration; existing rows need the old flag to preserve manual amounts.
	if not frappe.db.has_column(doctype, 'override'):
		if frappe.db.exists(doctype, {'parenttype': 'Payment Settlement Entry'}):
			frappe.throw(frappe._('Field {0} does not exist on {1}').format('override', doctype))
		return

	component = frappe.qb.DocType(doctype)
	method = (
		Case()
		.when((component.type == 'Clearing') & (component.calculation_method == 'Manual'), 'Automatic')
		.when((component.type == 'Settlement') & (component.override == 1), 'Manual')
		.when(component.type == 'Settlement', 'Automatic')
		.when(component.type == 'Adjustment', 'Manual')
		.else_(component.calculation_method)
	)

	# No docstatus filter or Document.save(): preserve amounts, journals, and audit timestamps.
	(
		frappe.qb.update(component)
		.set(component.calculation_method, method)
		.where(component.parenttype == 'Payment Settlement Entry')
		.where(component.type.isin(('Clearing', 'Settlement', 'Adjustment')))
	).run()
