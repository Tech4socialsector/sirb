# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Whitelisted helpers for the Vue Project Details page. These sit
alongside (not instead of) the existing sirb.api endpoints
(get_irb_project_roles, get_project_students, set_project_status) reused
as-is from the legacy frontend.
"""

import json

import frappe

from sirb.api import get_irb_project_roles, get_project_students


def _link_titles(doc):
	"""Maps each populated Link fieldname on `doc` to the linked doc's
	display title (its title_field, e.g. Faculty.full_name), so the
	frontend never has to show raw autoincrement IDs like "8" for
	fields such as faculty_mentor/primary_reviewer/secondary_reviewer.
	"""
	titles = {}
	for df in doc.meta.fields:
		if df.fieldtype != "Link" or not doc.get(df.fieldname):
			continue
		value = doc.get(df.fieldname)
		try:
			target_meta = frappe.get_meta(df.options)
			title_field = target_meta.get_title_field()
			titles[df.fieldname] = frappe.db.get_value(df.options, value, title_field) or value
		except Exception:
			titles[df.fieldname] = value
	return titles


@frappe.whitelist()
def get_project_detail(project_name):
	"""Single aggregated payload for the Project Details page: the doc
	itself (server-filtered by permlevel — Frappe strips fields the
	current user can't read), the caller's role(s) on this project, and
	the student roster. Vue should treat any field absent from `doc` as
	"not visible to me", not "empty".
	"""
	doc = frappe.get_doc("IRB Project", project_name)
	doc.check_permission("read")

	roles = get_irb_project_roles(user=frappe.session.user, project_name=project_name)
	students = get_project_students(project_name)

	return {
		"doc": doc.as_dict(),
		"link_titles": _link_titles(doc),
		"roles": roles,
		"students": students,
		"meta": {
			"can_write": doc.has_permission("write"),
		},
	}


@frappe.whitelist()
def get_status_change_history(project_name):
	"""Status transition history for the Approval Timeline component,
	derived from the Version doctype the same way irb_admin_console's
	get_recent_activity() and the Projects by IRB Unit report already do.
	"""
	frappe.get_doc("IRB Project", project_name).check_permission("read")

	versions = frappe.db.sql(
		"""select data, owner, creation from `tabVersion`
		where ref_doctype = 'IRB Project' and docname = %(name)s
		order by creation asc""",
		{"name": project_name},
		as_dict=True,
	)

	history = []
	for v in versions:
		try:
			changed = json.loads(v["data"]).get("changed") or []
		except (TypeError, ValueError):
			continue
		for change in changed:
			if len(change) >= 3 and change[0] == "status":
				history.append(
					{
						"from_status": change[1],
						"to_status": change[2],
						"changed_by": v["owner"],
						"date": v["creation"],
					}
				)
	return history


@frappe.whitelist()
def get_field_changes_since_status(project_name, since_status):
	"""Field-level diffs recorded since the doc last held `since_status` —
	powers the "here's what changed" banners the legacy DocType JS shows
	students/mentors/reviewers (update_field_changes / get_versions_after_status_change).
	"""
	frappe.get_doc("IRB Project", project_name).check_permission("read")

	versions = frappe.db.sql(
		"""select data, modified from `tabVersion`
		where ref_doctype = 'IRB Project' and docname = %(name)s
		order by modified desc""",
		{"name": project_name},
		as_dict=True,
	)

	relevant = []
	for v in versions:
		try:
			changed = json.loads(v["data"]).get("changed") or []
		except (TypeError, ValueError):
			continue
		hit_boundary = any(c[0] == "status" and c[2] == since_status for c in changed)
		if hit_boundary:
			break
		relevant.append({"changed": changed, "date": v["modified"]})

	field_changes = {}
	for v in relevant:
		for change in v["changed"]:
			if len(change) < 3:
				continue
			fieldname = change[0]
			field_changes.setdefault(fieldname, []).append(
				{"old_value": change[1], "new_value": change[2], "date": v["date"]}
			)
	return field_changes
