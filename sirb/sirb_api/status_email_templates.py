# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""E-mail templates for IRB Project status changes (IRBProject.on_change) and
for a student joining a project (StudentProjectMapping.after_insert).

status_email_templates.json holds the live site's copies (exported 2026-09-25).
Like the Timeline Alert defaults (see alert_templates), they are seeded only
when missing and never updated, so edits made in Desk survive every
`bench migrate`; they are not fixtures for the same reason.
"""

import json
import os

import frappe

_DATA_FILE = os.path.join(os.path.dirname(__file__), "status_email_templates.json")

# The params IRBProject / StudentProjectMapping pass to send_email_if_configured.
STATUS_EMAIL_VARIABLES = [
	("student_names", "Comma-separated names of the project's students"),
	("project_name", "Project title"),
	("project_status", "Project status (the new one, on a status change)"),
	("project_url", "Link to the project in the IRB portal"),
]


def get_status_email_templates():
	with open(_DATA_FILE, encoding="utf-8") as f:
		return json.load(f)


def ensure_status_email_templates():
	"""Create the status e-mail templates that don't exist. Never updates one."""
	created = []
	for tpl in get_status_email_templates():
		if frappe.db.exists("Email Template", tpl["name"]):
			continue
		doc = frappe.get_doc({"doctype": "Email Template", **tpl})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created
