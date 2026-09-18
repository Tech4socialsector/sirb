import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw("Log in to continue", frappe.PermissionError)

	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # nosemgrep

	context.boot = {
		"csrf_token": csrf_token,
		"sitename": frappe.local.site,
	}
