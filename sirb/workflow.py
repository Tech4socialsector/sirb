# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Server-side IRB Project status workflow.

`status` is read-only in the form, but Frappe doesn't enforce read_only
on the server — and every Student / Faculty Mentor / Reviewer role has
write access to IRB Project — so without this check anyone could move
any project to any status (e.g. a student approving their own project)
through sirb.api.set_project_status or frappe.client.set_value.

The table mirrors the action buttons in the portal
(frontend/src/composables/useProjectActions.ts), which only shows the
buttons whose target is in the `allowed_statuses` this module returns
with the project (sirb_api.project.get_project_detail).
"""

import frappe

PROPOSAL = "Awaiting proposal completion by student"
MENTOR_APPROVAL = "Awaiting Faculty mentor approval"
STUDENT_FIX_MENTOR = "Awaiting student correction for mentor feedback"
STUDENT_FIX_REVIEWER = "Awaiting student correction for reviewer feedback"
REVIEWER_FEEDBACK = "Awaiting reviewer feedback to student"
PRIMARY_TO_SECONDARY = "Awaiting primary reviewer comments to secondary reviewer"
SECONDARY_TO_PRIMARY = "Awaiting secondary reviewer comments to primary reviewer"
PROVISIONAL = "Provisionally approved"
FINAL_APPROVAL = "Awaiting final approval"
APPROVED = "Approved"

BYPASS_ROLES = {"System Manager", "Administrator"}


def _after_mentor(doc):
	return PRIMARY_TO_SECONDARY if doc.get("secondary_reviewer") else REVIEWER_FEEDBACK


def _student_submit_target(doc):
	"""Where a finished proposal goes, from the IRB Unit's rules — the same
	logic as the Desk form's "Request … Approval" button."""
	unit = doc.get("irb_unit") and frappe.db.get_value(
		"IRB Unit", doc.get("irb_unit"), ["mentor_required", "num_reviewers"], as_dict=True
	)
	if not unit:
		return MENTOR_APPROVAL if doc.get("faculty_mentor") else REVIEWER_FEEDBACK
	if unit.mentor_required:
		return MENTOR_APPROVAL
	return PRIMARY_TO_SECONDARY if str(unit.num_reviewers or "1").strip() == "2" else REVIEWER_FEEDBACK


def allowed_transitions(doc, roles):
	"""{target statuses} the holder of `roles` (their roles ON THIS
	project, from sirb.api.get_irb_project_roles) may move `doc` to from
	its current status."""
	status = doc.get("status")
	allowed = set()

	if roles.get("is_student"):
		if status == PROPOSAL:
			allowed.add(_student_submit_target(doc))
		elif status == STUDENT_FIX_MENTOR:
			allowed.add(MENTOR_APPROVAL)
		elif status == STUDENT_FIX_REVIEWER:
			allowed.add(REVIEWER_FEEDBACK)
		elif status == PROVISIONAL:
			allowed.add(FINAL_APPROVAL)

	if roles.get("is_mentor") and status == MENTOR_APPROVAL:
		allowed.update({_after_mentor(doc), STUDENT_FIX_MENTOR})

	if roles.get("is_primary_reviewer"):
		if status == REVIEWER_FEEDBACK:
			allowed.update({STUDENT_FIX_REVIEWER, APPROVED, PROVISIONAL})
		elif status in (FINAL_APPROVAL, PROVISIONAL):
			allowed.add(APPROVED)
		elif status == PRIMARY_TO_SECONDARY:
			allowed.add(SECONDARY_TO_PRIMARY)

	if roles.get("is_secondary_reviewer") and status == SECONDARY_TO_PRIMARY:
		allowed.add(REVIEWER_FEEDBACK)

	return allowed


def validate_status_change(doc):
	"""Throw unless the current user may move `doc` from its saved status
	to its new one. Admins, imports, patches and system jobs are exempt."""
	if doc.is_new() or doc.flags.ignore_permissions or doc.flags.script_created:
		return
	if frappe.flags.in_import or frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_install:
		return
	if set(frappe.get_roles()) & BYPASS_ROLES:
		return

	before = doc.get_doc_before_save()
	if not before or before.status == doc.status:
		return

	from sirb.api import get_irb_project_roles

	roles = get_irb_project_roles(user=frappe.session.user, project_name=doc.name) or {}
	if doc.status in allowed_transitions(before, roles):
		return

	if not any(roles.values()):
		frappe.throw(
			"You are not assigned to this project, so you can't change its status.",
			frappe.PermissionError,
			title="Not allowed",
		)
	frappe.throw(
		f"This project can't move from “{before.status}” to “{doc.status}” with your role on it. "
		"Reload the page to see the actions currently available to you.",
		frappe.PermissionError,
		title="Not allowed",
	)
