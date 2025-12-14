frappe.ready(async function () {

    let perms = await frappe.call({
        method: "sirb.api.get_field_permissions_from_doctype",
		args: {
 			'doctype': 'Project',
		}
    });
	console.log(perms, perms.message);

    perms = perms.message;

    for (let fieldname in perms) {
        let p = perms[fieldname];
        console.log("Permissions for ");
        console.log(fieldname, p);

        // Hide field if no read permission
        if (!p.read) {
            $(`[data-fieldname="${fieldname}"]`).hide();
			// continue;
        }

        // Make read-only if no write permission
        if (p.read && !p.write) {
            frappe.web_form.set_df_property(fieldname, "read_only", 1);
        }
    }

});
	
