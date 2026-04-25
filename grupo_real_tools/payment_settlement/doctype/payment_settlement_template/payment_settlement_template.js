frappe.ui.form.on('Payment Settlement Template', {
	company(frm) {
		frm.set_value({
			bank_account: '',
			settlement_account: '',
		});
		frm.clear_table('components');
		frm.refresh_fields();
	},
	mode_of_payment(frm) {
		frm.set_value('clearing_account', '');
		frm.refresh_field('clearing_account');
	}
});
