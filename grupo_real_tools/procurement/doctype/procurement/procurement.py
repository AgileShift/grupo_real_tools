from frappe.model.document import Document
from frappe.utils import flt


class Procurement(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from grupo_real_tools.procurement.doctype.procurement_item.procurement_item import ProcurementItem
		from grupo_real_tools.procurement.doctype.procurement_item_proposal.procurement_item_proposal import ProcurementItemProposal

		company: DF.Link
		discount: DF.Currency
		item_proposals: DF.Table[ProcurementItemProposal]
		items: DF.Table[ProcurementItem]
		subtotal: DF.Currency
		supplier: DF.Link
		supplier_invoice: DF.Data
		supplier_invoice_date: DF.Date
		total: DF.Currency
		total_qty: DF.Float
		transportation_method: DF.Literal["SEA", "AIR"]
		transporter_invoice_date: DF.Date | None
		transporter_invoice_no: DF.Data | None
	# end: auto-generated types

	def before_validate(self):
		self.total_qty, self.subtotal, self.discount, self.total = 0.00, 0.00, 0.00, 0.00

		for proposal in self.item_proposals:
			proposal.subtotal = flt(proposal.qty) * flt(proposal.purchase_rate)
			self.total_qty += flt(proposal.qty)
			self.subtotal += proposal.subtotal

		self.total = self.subtotal
