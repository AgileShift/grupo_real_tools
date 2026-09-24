frappe.ui.form.on("Payment Settlement Entry", {
	setup(frm) {
		frm.page.sidebar.toggle(false);

		// References are fetched from the backend, not added manually.
		frm.set_df_property('references', 'cannot_add_rows', true);

		// Apply To selects the clearing account whose settlement absorbs this component.
		frm.set_query('apply_to', 'components', (doc) => ({
			filters: {
				name: ['in', (doc.accounts || []).map((row) => row.clearing_account).filter(Boolean)]
			}
		}));
	},

	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 0)
			return;

		frm.add_custom_button(__('Get Entries'), () => {
			// The server replaces the references; mark the form dirty so they can be saved.
			return frm.events.fetch_references(frm).then(() => frm.dirty());
		});
	},

	company(frm) {
		// Clearing the Template also resets the rows copied from its previous company.
		frm.set_value('template', '');
	},

	template(frm) {
		// The Template replaces account and component rows; reload references for those mappings.
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
		// The server appends the adjustment row; mark the form dirty so it can be saved.
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

	fetch_references(frm) {
		// Incomplete filters invalidate current references; clear them and recalculate.
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
	before_components_remove(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (['Clearing', 'Settlement'].includes(row.type)) {
			frappe.throw(__('Cannot delete {0}', [`${__(row.type)}: ${row.account}`]));
		}
	},
	components_remove: frappe.utils.debounce((frm) => frm.call('calculate'), 250), // Bulk delete fires once per row; recalculate after the grid settles.
	exchange_rate(frm) {
		return frm.call('calculate'); // Recalculate base amounts and settlement residuals after a rate change.
	},
});
