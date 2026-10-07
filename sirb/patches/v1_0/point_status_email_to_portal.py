# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Point the faculty status-change e-mail's "click here to review" link at the
project in the IRB portal ({{ project_url }}, /sirb/projects/<id>) instead of
the Desk at /app. Only that exact link is replaced, so any other edits made to
the template in Desk are kept; a template without it is left alone."""

import frappe

TEMPLATE = "Status Change Email Template"
OLD_LINK = "https://student-irb.m.frappe.cloud/app/"
NEW_LINK = "{{ project_url }}"


def execute():
	if not frappe.db.exists("Email Template", TEMPLATE):
		return
	for field in ("response_html", "response"):
		value = frappe.db.get_value("Email Template", TEMPLATE, field)
		if value and OLD_LINK in value:
			frappe.db.set_value("Email Template", TEMPLATE, field, value.replace(OLD_LINK, NEW_LINK))
