frappe.ui.form.on("Payment Settlement Template", {
	setup(frm) {
		// Hide payment modes already selected in the Template's account rows.
		frm.set_query('mode_of_payment', 'accounts', (doc) => ({
			filters: {
				name: ['not in', doc.accounts.map((row) => row.mode_of_payment).filter(Boolean)]
			}
		}));

		// Keep component accounts separate from structural clearing and settlement accounts.
		frm.set_query('account', 'components', (doc) => ({
			filters: {
				name: ['not in', doc.accounts.flatMap((row) => [row.clearing_account, row.settlement_account]).filter(Boolean)]
			}
		}));

		// Apply To selects the clearing account whose settlement absorbs this component.
		frm.set_query('apply_to', 'components', (doc) => ({
			filters: {
				name: ['in', (doc.accounts || []).map((row) => row.clearing_account).filter(Boolean)]
			}
		}));
	},

	company(frm) {
		// Account mappings and components must be configured again for the new company.
		frm.clear_table('accounts');
		frm.clear_table('components');
		frm.refresh_fields();
	}
});

frappe.ui.form.on("Payment Settlement Template Account", {
	mode_of_payment(frm, cdt, cdn) {
		// Use the grid Link control so setting the clearing account also fetches its currency.
		const grid_row = frm.fields_dict.accounts.grid.grid_rows_by_docname[cdn];
		const clearing_account_field = grid_row.get_field('clearing_account');
		const row = grid_row.doc;

		if (!row.mode_of_payment) {
			// Removing the payment mode also clears its derived account and currency.
			return clearing_account_field.set_value('');
		}

		// ERPNext resolves the payment-mode account; the backend repeats this on save.
		frappe.xcall("erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account", {
			mode_of_payment: row.mode_of_payment,
			company: frm.doc.company,
		}).then(({ account }) => clearing_account_field.set_value(account));
	},

	settlement_account(frm, cdt, cdn) {
		const grid_row = frm.fields_dict.accounts.grid.grid_rows_by_docname[cdn];
		const settlement_account = grid_row.get_field('settlement_account');

		// A Bank Account may fill this Link indirectly; validate it to fetch its currency.
		return settlement_account.validate(grid_row.doc.settlement_account);
	}
});
