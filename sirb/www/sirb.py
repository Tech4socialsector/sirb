from urllib.parse import quote

import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		# Send guests to the login page and back to the page they asked for
		# (e.g. a /sirb/projects/<id> link from an email), rather than a bare
		# "not permitted" error page.
		path = frappe.request.path if getattr(frappe, "request", None) else "/sirb"
		if frappe.request and frappe.request.query_string:
			path += "?" + frappe.request.query_string.decode()
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(path, safe="")
		# 302, not the default 301: a cached permanent redirect would keep
		# bouncing the browser to /login even after the user signs in.
		raise frappe.Redirect(302)

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
