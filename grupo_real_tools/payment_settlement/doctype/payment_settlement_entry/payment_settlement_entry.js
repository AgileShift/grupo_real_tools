frappe.ui.form.on("Payment Settlement Entry", {
	setup(frm) {
		frm.page.sidebar.toggle(false); // Hide Sidebar

		frm.set_df_property('references', 'cannot_add_rows', true);
	},

	refresh(frm) {
		if (frm.is_new())
			return;

		frm.add_custom_button(__('Get Entries'), () => {
			frm.events.fetch_references(frm);
		});
	},

	company(frm) {
		frm.set_value('template', '');
	},

	template(frm) {
		return frm.call('fetch_template_data').then(() => {
			frm.events.fetch_references(frm);
		});
	},

	from_date(frm) {
		frm.events.fetch_references(frm);
	},

	to_date(frm) {
		frm.events.fetch_references(frm);
	},

	// Custom Functions

	fetch_references(frm) {
		if (!frm.doc.from_date || !frm.doc.to_date || !frm.doc.template || !frm.doc.accounts?.length) {
			frm.clear_table('references');
			return frm.call('calculate_account_totals');
		}

		return frm.call('fetch_references');
	}
});

frappe.ui.form.on('Payment Settlement Entry Reference', {
	references_remove(frm) {
		return frm.call('calculate_account_totals');
	},
});
