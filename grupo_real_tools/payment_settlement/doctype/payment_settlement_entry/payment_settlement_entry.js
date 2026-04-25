frappe.ui.form.on('Payment Settlement Entry', {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.events.fetch_payment_sources(frm);
	},

	fetch_payment_sources(frm) {
		frm.add_custom_button(__('Fetch Payments'), () => {
			if (!frm.doc.company || !frm.doc.mode_of_payment || !frm.doc.from_date || !frm.doc.to_date) {
				frappe.msgprint(__('Set Company, Mode of Payment, From Date and To Date first.'));
				return;
			}

			frm.call('fetch_payment_sources').then((r) => {
				const totals = r.message?.totals || {};
				frappe.msgprint({
					title: __('Payments Fetched'),
					indicator: 'green',
					message: __(
						'Payment Entries: {0}<br>Sales Invoice Payments: {1}<br>Total Amount (Company Currency): {2}',
						[
							totals.payment_entries_count || 0,
							totals.sales_invoice_payments_count || 0,
							format_currency(totals.base_amount || 0),
						]
					),
				});
			});
		});
	}
});
