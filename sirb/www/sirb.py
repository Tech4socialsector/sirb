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
		# Exposed so the frontend's realtime (socket.io) client can connect
		# to the actual configured port (sites/common_site_config.json ->
		# socketio_port) instead of silently falling back to a wrong
		# default — see src/composables/useRealtime.ts.
		"socketio_port": frappe.conf.socketio_port,
		# frappe-ui's initSocket() reads *this exact* key (not "sitename")
		# to pick the socket.io namespace. Every realtime event Frappe
		# publishes is routed to a namespace named after frappe.local.site
		# (see frappe/realtime.py), so without this the browser connects
		# to namespace "/undefined" and silently never receives anything
		# published to the real site's namespace — no error, just nothing.
		"site_name": frappe.local.site,
	}
