# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Whitelisted helpers for the Vue Project Details page. These sit
alongside (not instead of) the existing sirb.api endpoints
(get_irb_project_roles, get_project_students, set_project_status) reused
as-is from the legacy frontend.
"""

import json

import frappe

from sirb.api import _get_irb_project_roles, get_project_students
from sirb.permissions import (
	can_open_all_review_sections,
	hidden_project_fields,
	manages_project,
	person_masker,
	writable_permlevels,
)
from sirb.workflow import (
	MENTOR_APPROVAL,
	PROPOSAL,
	REVIEWER_FEEDBACK,
	STUDENT_FIX_MENTOR,
	STUDENT_FIX_REVIEWER,
	allowed_transitions,
)


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


STAFF_ROLES = {"System Manager", "Administrator"}


@frappe.whitelist()
def get_project_detail(project_name):
	"""Single aggregated payload for the Project Details page: the doc
	itself (minus the fields this user may not see on it — see
	sirb.permissions.hidden_project_fields), the caller's role(s) on this
	project, and the student roster. Vue should treat any field absent from `doc` as "not
	visible to me", not "empty".
	"""
	doc = frappe.get_doc("IRB Project", project_name)
	doc.check_permission("read")

	roles = _get_irb_project_roles(frappe.session.user, project_name)
	students = get_project_students(project_name)

	doc_dict = doc.as_dict()
	link_titles = _link_titles(doc)
	hidden = hidden_project_fields(doc)
	if hidden:
		for fieldname in hidden:
			doc_dict.pop(fieldname, None)
			link_titles.pop(fieldname, None)
		# The last editor may be someone they may not see (e.g. a reviewer
		# sending corrections back).
		mask = person_masker(doc)
		for fieldname in ("owner", "modified_by"):
			doc_dict[fieldname] = mask(doc_dict.get(fieldname))

	return {
		"doc": doc_dict,
		"link_titles": link_titles,
		"roles": roles,
		"students": students,
		"meta": {
			"can_write": doc.has_permission("write"),
			# Where the mentor's approval sends the project (sirb.workflow),
			# without revealing who the secondary reviewer is.
			"has_secondary_reviewer": bool(doc.get("secondary_reviewer")),
			# Edits to fields at other permlevels are dropped on save, so the
			# page shows those fields read-only.
			"writable_permlevels": sorted(writable_permlevels(doc)),
			# Admin-style edits (reassign mentor/reviewers, set any status):
			# admins, and programme managers on their programmes' projects.
			"can_override": bool(STAFF_ROLES & set(frappe.get_roles())) or manages_project(frappe.session.user, doc),
			# "Toggle All Sections", as on the Desk form.
			"can_open_all_review_sections": can_open_all_review_sections(doc),
		},
		# Status changes this user may make right now — the server enforces
		# exactly this set (sirb.workflow), so the UI shows only these.
		"allowed_statuses": sorted(allowed_transitions(doc, roles or {})),
	}


@frappe.whitelist()
def get_status_change_history(project_name):
	"""Status transition history for the Approval Timeline component,
	derived from the Version doctype the same way irb_admin_console's
	get_recent_activity() and the Projects by IRB Unit report already do.
	"""
	doc = frappe.get_doc("IRB Project", project_name)
	doc.check_permission("read")
	display_user = person_masker(doc)

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
						"changed_by": display_user(v["owner"]),
						"date": v["creation"],
					}
				)
	return history


# Old name -> current name, for Versions saved before a field was renamed.
_RENAMED_FIELDS = {"heq_s18_": "heq_s18_mf"}


def _changes_since(doc, is_boundary, exclude_owner=None):
	"""Changes recorded on `doc` after the newest Version whose status
	change (old, new) satisfies `is_boundary`, newest first, as
	({fieldname: [{old_value, new_value, date}]}, boundary_found). Fields
	this user may not read are left out, as are edits by `exclude_owner`."""
	hidden = hidden_project_fields(doc)
	readable = set(doc.get_permlevel_access("read")) | {0}

	versions = frappe.db.sql(
		"""select data, owner, modified from `tabVersion`
		where ref_doctype = 'IRB Project' and docname = %(name)s
		order by modified desc""",
		{"name": str(doc.name)},
		as_dict=True,
	)

	field_changes = {}
	for v in versions:
		try:
			changed = json.loads(v["data"]).get("changed") or []
		except (TypeError, ValueError):
			continue
		changed = [c for c in changed if len(c) >= 3]
		if any(c[0] == "status" and is_boundary(c[1], c[2]) for c in changed):
			return field_changes, True
		if exclude_owner and v["owner"] == exclude_owner:
			continue
		for fieldname, old_value, new_value in (c[:3] for c in changed):
			fieldname = _RENAMED_FIELDS.get(fieldname, fieldname)
			df = doc.meta.get_field(fieldname)
			if not df or df.permlevel not in readable:
				continue
			if fieldname in hidden:
				continue
			field_changes.setdefault(fieldname, []).append(
				{"old_value": old_value, "new_value": new_value, "date": v["modified"]}
			)
	return field_changes, False


@frappe.whitelist()
def get_field_changes_since_status(project_name, since_status):
	"""Field-level diffs recorded since the doc last held `since_status`."""
	doc = frappe.get_doc("IRB Project", project_name)
	doc.check_permission("read")
	return _changes_since(doc, lambda old, new: new == since_status)[0]


# Statuses in which the proposal is with the student or their mentor; it
# reaches the reviewers when it leaves them.
_BEFORE_REVIEW = {PROPOSAL, MENTOR_APPROVAL, STUDENT_FIX_MENTOR, STUDENT_FIX_REVIEWER}

# For each status: the status change (old, new) that handed the project to
# whoever acts on it now. What others changed since then is what they need
# to look at.
_ROUND_START = {
	# Mentor feedback: since the student last sent it to the mentor.
	STUDENT_FIX_MENTOR: lambda old, new: new == MENTOR_APPROVAL,
	# Reviewer feedback: since it reached the reviewers. With two reviewers
	# that is before the primary's notes to the secondary, not when the
	# secondary passes it back, so the primary's early feedback counts.
	STUDENT_FIX_REVIEWER: lambda old, new: old in _BEFORE_REVIEW and new not in _BEFORE_REVIEW,
	# Mentor / reviewer: the student's corrections since they asked for them.
	MENTOR_APPROVAL: lambda old, new: new == STUDENT_FIX_MENTOR,
	REVIEWER_FEEDBACK: lambda old, new: new == STUDENT_FIX_REVIEWER,
}


@frappe.whitelist()
def get_review_highlights(project_name):
	"""What others changed on this project since it was last handed to the
	people who act on it now — the reviewer's feedback for a student asked
	for corrections, the student's corrections for the reviewer or mentor.
	{fieldname: [{old_value, new_value, date}]}, newest first; empty when
	nothing is being returned (e.g. a first submission).

	Done here rather than in the browser so it needs no read access to
	Version, which can't be limited to one's own projects."""
	doc = frappe.get_doc("IRB Project", project_name)
	doc.check_permission("read")
	is_boundary = _ROUND_START.get(doc.status)
	if not is_boundary:
		return {}
	changes, found = _changes_since(doc, is_boundary, exclude_owner=frappe.session.user)
	changes.pop("status", None)
	if found or doc.status in (STUDENT_FIX_MENTOR, STUDENT_FIX_REVIEWER):
		# A student's feedback still shows if the hand-over was never
		# recorded (e.g. a status set by import): it's all others wrote.
		return changes
	# Otherwise this is the first submission: everything would be "new".
	return {}


@frappe.whitelist()
def get_proposal_issues(project_name):
	"""Unanswered questions that would block the student from submitting,
	using the exact rules IRBProject.validate enforces on submit (see
	sirb.proposal_checks). Read-only; evaluated against the saved doc."""
	from sirb.proposal_checks import get_proposal_issues as _issues

	doc = frappe.get_doc("IRB Project", project_name)
	doc.check_permission("read")
	return _issues(doc)
