frappe.ui.form.on("Payment Settlement Template", {
	onload(frm) {
		// Prevent selecting the same Mode of Payment more than once.
		frm.set_query('mode_of_payment', 'accounts', (doc) => ({
			filters: {
				name: ['not in', doc.accounts.map((row) => row.mode_of_payment).filter(Boolean)]
			}
		}));

		// Prevent components from using an account already assigned as a clearing account.
		frm.set_query('account', 'components', (doc) => ({
			filters: {
				name: ['not in', doc.accounts.map((row) => row.clearing_account).filter(Boolean)]
			}
		}));
	},

	company(frm) {
		// Child rows depend on the company and must be configured again.
		frm.clear_table('accounts');
		frm.clear_table('components');
		frm.refresh_fields();
	}
});

frappe.ui.form.on("Payment Settlement Template Account", {
	mode_of_payment(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (!row.mode_of_payment) {
			// Keep the derived clearing account empty when no payment mode is selected.
			frappe.model.set_value(cdt, cdn, 'clearing_account', '', 'Link');
			return;
		}

		// Use configured account for this payment mode; Backend and assigns it again during validation
		frappe.xcall("erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account", {
			mode_of_payment: row.mode_of_payment,
			company: frm.doc.company,
		}).then((r) => {
			frappe.model.set_value(cdt, cdn, 'clearing_account', r.account, 'Link')
		});
	}
});
