frappe.ui.form.on("Payment Settlement Template", {
	setup(frm) {
		// Prevent selecting the same Mode of Payment more than once.
		frm.set_query('mode_of_payment', 'accounts', (doc) => ({
			filters: {
				name: ['not in', doc.accounts.map((row) => row.mode_of_payment).filter(Boolean)]
			}
		}));

		// Prevent components from using an account already assigned as: clearing or settlement account
		frm.set_query('account', 'components', (doc) => ({
			filters: {
				name: ['not in', doc.accounts.flatMap((row) => [row.clearing_account, row.settlement_account]).filter(Boolean)]
			}
		}));

		// Prevent Apply debit or credit calculations to accounts other than clearing accounts
		frm.set_query('apply_to', 'components', (doc) => ({
			filters: {
				name: ['in', (doc.accounts || []).map((row) => row.clearing_account).filter(Boolean)]
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
		const grid_row = frm.fields_dict.accounts.grid.grid_rows_by_docname[cdn];
		const clearing_account_field = grid_row.get_field('clearing_account');
		const row = grid_row.doc;

		if (!row.mode_of_payment) {
			// Keep the derived clearing account empty when no payment mode is selected.
			return clearing_account_field.set_value('');
		}

		// Use configured account for this payment mode; Backend and assigns it again during validation
		frappe.xcall("erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account", {
			mode_of_payment: row.mode_of_payment,
			company: frm.doc.company,
		}).then(({ account }) => clearing_account_field.set_value(account));
	},

	settlement_account(frm, cdt, cdn) {
		const grid_row = frm.fields_dict.accounts.grid.grid_rows_by_docname[cdn];
		const settlement_account = grid_row.get_field('settlement_account');

		return settlement_account.validate(grid_row.doc.settlement_account);
	}
});
