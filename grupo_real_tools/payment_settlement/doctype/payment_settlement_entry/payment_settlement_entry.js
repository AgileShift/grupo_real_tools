frappe.ui.form.on("Payment Settlement Entry", {
	setup(frm) {
		frm.page.sidebar.toggle(false); // Hide Sidebar

		frm.set_df_property('references', 'cannot_add_rows', true);

		frm.set_query('apply_to', 'components', (doc) => ({
			filters: {
				name: ['in', (doc.accounts || []).map((row) => row.clearing_account).filter(Boolean)]
			}
		}));
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

	make_difference(frm) {
		frappe.prompt({
				fieldname: 'adjustment_type',
				fieldtype: 'Select',
				label: __('Select Difference Account'),
				reqd: 1,
				options: [
					'Round Off',
					'Exchange Gain Or Loss',
					'Write Off'
				]
			},
			({adjustment_type}) => frm.call('make_difference', {adjustment_type}).then(() => frm.dirty()),
			__('Make Difference Entry'),
			__('Apply')
		);
	},

	// Custom Functions
	fetch_references(frm) {
		if (!frm.doc.from_date || !frm.doc.to_date || !frm.doc.template || !frm.doc.accounts?.length) {
			frm.clear_table('references');
			return frm.call('calculate');
		}

		return frm.call('fetch_references');
	},
});

frappe.ui.form.on('Payment Settlement Entry Reference', {
	references_remove(frm) {
		return frm.call('calculate');
	},
});

frappe.ui.form.on('Payment Settlement Entry Component', {
	exchange_rate(frm) {
		return frm.call('calculate');
	},
	components_remove(frm) {
		return frm.call('calculate');
	},
});
