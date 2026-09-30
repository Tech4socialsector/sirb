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
from sirb.permissions import project_membership
from sirb.workflow import allowed_transitions


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


# Label shown to students in place of whoever reviewed their project.
REVIEWER_LABEL = "IRB Reviewer"
REVIEWER_ROLES = {"Primary IRB Reviewer", "Secondary IRB Reviewer"}
STAFF_ROLES = {"System Manager", "Administrator"}


def _hide_reviewers_from(doc):
	"""True when the caller sees this project only as its student. The
	Student role has read on every permlevel of IRB Project and as_dict()
	applies no field filtering, so these helpers hide reviewer identities
	and the reviewers' internal notes from students. Membership ignores the
	mapping's status, so this still holds after the project is approved
	(approval deactivates the student's mapping)."""
	if STAFF_ROLES & set(frappe.get_roles()):
		return False
	membership = project_membership(frappe.session.user, doc)
	if membership["is_mentor"] or membership["is_primary_reviewer"] or membership["is_secondary_reviewer"]:
		return False
	return membership["is_student"]


def _reviewer_masker(doc):
	"""Maps a user id to what a student may see: a reviewer's own identity
	becomes REVIEWER_LABEL; everyone else (students, the mentor, admins) is
	shown as-is."""
	mentor_user = doc.get("faculty_mentor") and frappe.db.get_value("Faculty", doc.faculty_mentor, "system_user")
	cache = {}

	def mask(user):
		if not user or user == mentor_user:
			return user
		if user not in cache:
			cache[user] = bool(REVIEWER_ROLES & set(frappe.get_roles(user)))
		return REVIEWER_LABEL if cache[user] else user

	return mask


def _is_reviewer_only_field(fieldname):
	"""Who the reviewers are, plus the notes they exchange between
	themselves (_prn/_srn), as opposed to feedback meant for the student."""
	return (
		fieldname
		in (
			"primary_reviewer",
			"secondary_reviewer",
			"num_reviewers",
			"primary_reviewers_comments_to_secondary_reviewer",
			"secondary_reviewers_comments_to_primary_reviewer",
			"mentor_comments_to_reviewers",
		)
		or fieldname.endswith("_prn")
		or fieldname.endswith("_srn")
	)


@frappe.whitelist()
def get_project_detail(project_name):
	"""Single aggregated payload for the Project Details page: the doc
	itself (minus reviewer-only fields for students — see
	_hide_reviewers_from), the caller's role(s) on this project, and the
	student roster. Vue should treat any field absent from `doc` as "not
	visible to me", not "empty".
	"""
	doc = frappe.get_doc("IRB Project", project_name)
	doc.check_permission("read")

	roles = _get_irb_project_roles(frappe.session.user, project_name)
	students = get_project_students(project_name)

	doc_dict = doc.as_dict()
	link_titles = _link_titles(doc)
	if _hide_reviewers_from(doc):
		for fieldname in [f for f in doc_dict if _is_reviewer_only_field(f)]:
			doc_dict.pop(fieldname)
		for fieldname in [f for f in link_titles if _is_reviewer_only_field(f)]:
			link_titles.pop(fieldname)
		# The last editor may be a reviewer (e.g. sending corrections back).
		mask = _reviewer_masker(doc)
		for fieldname in ("owner", "modified_by"):
			doc_dict[fieldname] = mask(doc_dict.get(fieldname))

	return {
		"doc": doc_dict,
		"link_titles": link_titles,
		"roles": roles,
		"students": students,
		"meta": {
			"can_write": doc.has_permission("write"),
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
	display_user = _reviewer_masker(doc) if _hide_reviewers_from(doc) else (lambda user: user)

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


@frappe.whitelist()
def get_field_changes_since_status(project_name, since_status):
	"""Field-level diffs recorded since the doc last held `since_status` —
	powers the "here's what changed" banners the legacy DocType JS shows
	students/mentors/reviewers (update_field_changes / get_versions_after_status_change).
	"""
	doc = frappe.get_doc("IRB Project", project_name)
	doc.check_permission("read")
	hide_reviewers = _hide_reviewers_from(doc)

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
			if hide_reviewers and _is_reviewer_only_field(fieldname):
				continue
			field_changes.setdefault(fieldname, []).append(
				{"old_value": change[1], "new_value": change[2], "date": v["date"]}
			)
	return field_changes


@frappe.whitelist()
def get_proposal_issues(project_name):
	"""Unanswered questions that would block the student from submitting,
	using the exact rules IRBProject.validate enforces on submit (see
	sirb.proposal_checks). Read-only; evaluated against the saved doc."""
	from sirb.proposal_checks import get_proposal_issues as _issues

	doc = frappe.get_doc("IRB Project", project_name)
	doc.check_permission("read")
	return _issues(doc)
