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

from sirb.permissions import manages_project

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
	to its new one. Admins, programme managers (on their programmes'
	projects), imports, patches and system jobs are exempt."""
	if doc.is_new() or doc.flags.ignore_permissions or doc.flags.script_created:
		return
	if frappe.flags.in_import or frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_install:
		return
	if set(frappe.get_roles()) & BYPASS_ROLES:
		return

	before = doc.get_doc_before_save()
	if not before or before.status == doc.status:
		return
	if manages_project(frappe.session.user, before):
		return

	from sirb.api import _get_irb_project_roles

	roles = _get_irb_project_roles(frappe.session.user, doc.name)
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


# Who must be assigned before a project can sit in each status — otherwise
# it waits on a person who doesn't exist and no one can move it on.
_REQUIRED_FOR_STATUS = {
	MENTOR_APPROVAL: ("faculty_mentor",),
	STUDENT_FIX_MENTOR: ("faculty_mentor",),
	REVIEWER_FEEDBACK: ("primary_reviewer",),
	STUDENT_FIX_REVIEWER: ("primary_reviewer",),
	PROVISIONAL: ("primary_reviewer",),
	FINAL_APPROVAL: ("primary_reviewer",),
	PRIMARY_TO_SECONDARY: ("primary_reviewer", "secondary_reviewer"),
	SECONDARY_TO_PRIMARY: ("primary_reviewer", "secondary_reviewer"),
}
_PERSON_LABELS = {
	"faculty_mentor": "a Faculty Mentor",
	"primary_reviewer": "a Primary Reviewer",
	"secondary_reviewer": "a Secondary Reviewer",
}


def _sets_status_directly(doc):
	"""Admins and programme managers pick any status, so they're the ones
	who could leave a project waiting on someone who isn't assigned."""
	if set(frappe.get_roles()) & BYPASS_ROLES:
		return True
	return manages_project(frappe.session.user, doc.get_doc_before_save() or doc)


def validate_assignments(doc):
	"""Reject mentor/reviewer combinations that break the workflow when
	they're changed, and — for admins setting the status directly — a
	status whose required people aren't assigned. Checks only what changed,
	so existing projects with odd legacy data still save normally."""
	if doc.is_new():
		return

	people = ("faculty_mentor", "primary_reviewer", "secondary_reviewer")
	if any(doc.has_value_changed(f) for f in people):
		mentor, primary, secondary = (str(doc.get(f)) if doc.get(f) else None for f in people)
		if primary and primary == secondary:
			frappe.throw("The Primary and Secondary Reviewer must be different people.", title="Invalid assignment")
		if mentor and mentor in (primary, secondary):
			frappe.throw("The Faculty Mentor can't also be a reviewer on the same project.", title="Invalid assignment")

	if doc.has_value_changed("status") and _sets_status_directly(doc):
		missing = [_PERSON_LABELS[f] for f in _REQUIRED_FOR_STATUS.get(doc.status, ()) if not doc.get(f)]
		if missing:
			frappe.throw(
				f"Assign {' and '.join(missing)} before moving this project to “{doc.status}”.",
				title="Missing assignment",
			)


# What the student reads when asked for corrections: each question's
# feedback box (a <section>_rf / _mf field) and the overall comment.
_FEEDBACK_FOR_STUDENT = {
	STUDENT_FIX_REVIEWER: (
		"_rf",
		"reviewers_comments_to_student",
		"in a question's “Reviewer feedback to student” box or in “Reviewer's comments to student” "
		"on the General comments tab. Notes to the other reviewer aren't shown to the student.",
	),
	STUDENT_FIX_MENTOR: (
		"_mf",
		"mentor_comment_to_student",
		"in a question's “Mentor Feedback” box or in “Mentor's comments to student” on the General comments tab. "
		"Comments to the reviewers aren't shown to the student.",
	),
}


def validate_feedback_for_student(doc):
	"""Throw if `doc` is being sent back to its student for corrections
	with nothing in it the student can read. Reviewers had written all their
	feedback as notes to the secondary reviewer (_prn), which students
	don't see, so the student was asked to correct without being told what.
	Admins, programme managers, imports and system jobs are exempt."""
	if doc.is_new() or doc.flags.ignore_permissions or doc.flags.script_created:
		return
	if doc.status not in _FEEDBACK_FOR_STUDENT or not doc.has_value_changed("status"):
		return
	if frappe.flags.in_import or frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_install:
		return
	if _sets_status_directly(doc):
		return

	suffix, overall, where = _FEEDBACK_FOR_STUDENT[doc.status]
	fields = [overall] + [df.fieldname for df in doc.meta.fields if df.fieldname.endswith(suffix)]
	if any(str(doc.get(f) or "").strip() for f in fields):
		return
	frappe.throw(
		f"The student wouldn't see any feedback. Before asking for corrections, write it {where}",
		title="No feedback for the student",
	)
