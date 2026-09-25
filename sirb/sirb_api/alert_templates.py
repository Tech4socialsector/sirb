# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Default e-mail templates for Timeline Alerts.

They are ordinary Email Template records, so a System Manager can edit,
rename or delete them from Desk (Email Template) like any other template.
`ensure_default_templates` only ever *creates* a template that doesn't
exist yet; it never touches an existing one, so edits survive every
`bench migrate`. (That is also why these are not fixtures: fixtures are
re-imported with force on every migrate and would overwrite the edits.)

It runs from `after_install` (new sites) and from a one-time patch
(existing sites) — not on every migrate, so a template an admin deleted on
purpose stays deleted.

Bodies use only markup Desk's rich-text editor keeps as-is (<p>, <strong>,
<a>, <ul>/<li>) — no <br>: the editor has no soft line breaks and would
split those lines into paragraphs on the first save. Every Jinja variable
is listed in timeline_alerts.TEMPLATE_VARIABLES.
"""

import frappe

SIGNATURE = "<p>Regards,</p><p>IRB Office</p>"

DEFAULT_TEMPLATES = [
	{
		"name": "Timeline Alert - Proposal Reminder",
		"subject": "Reminder: please complete your IRB proposal – {{ project_label }}",
		"response": (
			"<p>Dear {{ student_name }},</p>"
			"<p>This is a reminder that your IRB proposal for <strong>{{ project_label }}</strong> "
			"({{ programme }}) has not been submitted yet. It was last updated {{ last_updated_ago }}.</p>"
			"<p>Please complete every section of the proposal and submit it to your faculty mentor for review.</p>"
			'<p><a href="{{ project_url }}">Open your proposal</a></p>'
			"<p>If you have already submitted it or need help, please contact "
			'{{ mentor_name or "your faculty mentor" }} or the IRB office.</p>' + SIGNATURE
		),
	},
	{
		"name": "Timeline Alert - Feedback Correction Reminder",
		"subject": "Action needed: respond to the feedback on {{ project_label }}",
		"response": (
			"<p>Dear {{ student_name }},</p>"
			"<p>Your IRB project <strong>{{ project_label }}</strong> is waiting for your corrections.</p>"
			"<p>Current status: <strong>{{ project_status }}</strong></p><p>Last updated: {{ last_updated_ago }}</p>"
			"<p>Please read the comments on your proposal, make the requested changes and resubmit it "
			"so that the review can continue.</p>"
			'<p><a href="{{ project_url }}">View the feedback and update your proposal</a></p>'
			"<p>If anything in the feedback is unclear, please contact "
			'{{ mentor_name or "your faculty mentor" }}.</p>' + SIGNATURE
		),
	},
	{
		"name": "Timeline Alert - Inactivity Reminder",
		"subject": "Your IRB project needs attention – {{ project_label }}",
		"response": (
			"<p>Dear {{ student_name }},</p>"
			"<p>There has been no activity on your IRB project <strong>{{ project_label }}</strong> "
			"since {{ last_updated }} ({{ last_updated_ago }}).</p>"
			"<p>Current status: <strong>{{ project_status }}</strong></p>"
			"<p>Please log in, check what is pending and take the next step so that your project "
			"stays on track with the review timeline.</p>"
			'<p><a href="{{ project_url }}">Open your project</a></p>' + SIGNATURE
		),
	},
	{
		"name": "Timeline Alert - Project Status Update",
		"subject": "Update on your IRB project – {{ project_label }}",
		"response": (
			"<p>Dear {{ student_name }},</p>"
			"<p>Here is the current status of your IRB project:</p>"
			"<ul>"
			"<li><strong>Project:</strong> {{ project_label }}</li>"
			"<li><strong>Programme:</strong> {{ programme }}</li>"
			"<li><strong>Status:</strong> {{ project_status }}</li>"
			'<li><strong>Faculty mentor:</strong> {{ mentor_name or "Not assigned yet" }}</li>'
			"<li><strong>Last updated:</strong> {{ last_updated }}</li>"
			"</ul>"
			'<p><a href="{{ project_url }}">Open your project</a></p>' + SIGNATURE
		),
	},
]

# Uses the deadline variables, so it can only be sent by an alert linked to a
# timeline activity (Timelines → Remind picks it by default).
DEADLINE_TEMPLATE_NAME = "Timeline Alert - Deadline Reminder"
DEFAULT_TEMPLATES.append(
	{
		"name": DEADLINE_TEMPLATE_NAME,
		"subject": "Reminder: {{ deadline_activity }} – {{ deadline_date }}",
		"response": (
			"<p>Dear {{ student_name }},</p>"
			"<p>This is a reminder from the IRB timeline for {{ programme }}:</p>"
			"<p><strong>{{ deadline_activity }}: {{ deadline_date }} {{ deadline_time }}</strong> ({{ deadline_when }})</p>"
			"<p>Your IRB project <strong>{{ project_label }}</strong> is currently at: {{ project_status }}.</p>"
			"<p>Please complete what is needed before the deadline.</p>"
			'<p><a href="{{ project_url }}">Open your project</a></p>'
			"<p>If you have any questions, please contact "
			'{{ mentor_name or "your faculty mentor" }} or the IRB office.</p>' + SIGNATURE
		),
	}
)

DEFAULT_TEMPLATE_NAMES = [t["name"] for t in DEFAULT_TEMPLATES]


def ensure_default_templates(names=None):
	"""Create default templates that don't exist (all, or just `names`).
	Never updates one."""
	created = []
	for tpl in DEFAULT_TEMPLATES:
		if names is not None and tpl["name"] not in names:
			continue
		if frappe.db.exists("Email Template", tpl["name"]):
			continue
		doc = frappe.get_doc({"doctype": "Email Template", "use_html": 0, **tpl})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created
