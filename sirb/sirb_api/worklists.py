# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Whitelisted, parametrized wrappers around the existing worklist/role
Script Reports (Student Projects, Mentor's/Primary/Secondary Reviewer's
Pending Worklist, All (Un-)Approved * Projects).

These reproduce the exact query logic already reviewed in each report's
`execute()` function (same joins, same status filters, same
get_logged_in_doc()-based scoping to the current session user) so the Vue
frontend has a single clean whitelisted method per worklist instead of
depending on the generic query-report runner. No business logic changes;
only the string-interpolated SQL in the originals is rewritten with bind
parameters here.
"""

import frappe

from sirb.utils import get_logged_in_doc

PRIMARY_REVIEWER_PENDING_STATUSES = [
	"Awaiting primary reviewer comments to secondary reviewer",
	"Awaiting final approval",
	"Awaiting reviewer feedback to student",
]
SECONDARY_REVIEWER_PENDING_STATUS = "Awaiting secondary reviewer comments to primary reviewer"
MENTOR_PENDING_STATUS = "Awaiting Faculty mentor approval"

PROJECT_ROW_FIELDS = """
	select s.name as student_id, s.full_name as student_name,
		p.title as project_title, p.name as project_name, p.status as project_status,
		p.irb_cycle as irb_cycle, p.modified as last_updated
	from tabStudent as s
	join `tabStudent Project Mapping` as sp on sp.student = s.name
	join `tabIRB Project` as p on sp.irb_project = p.name
	join tabFaculty as f on {role_join}
"""


def _role_scoped_projects(role_field, doc, status_clause, status_params=None):
	"""Shared query shape used by every mentor/reviewer worklist below."""
	if not doc:
		return []
	params = {"system_user": doc.system_user}
	if status_params:
		params.update(status_params)
	query = (
		PROJECT_ROW_FIELDS.format(role_join=f"p.{role_field} = f.name")
		+ " where f.system_user = %(system_user)s and sp.status = 'active' " + status_clause
	)
	return frappe.db.sql(query, params, as_dict=True)


@frappe.whitelist()
def get_student_projects():
	"""Student's own active (or approved) projects — mirrors the
	"Student Projects" report exactly, parametrized."""
	doc = get_logged_in_doc("Student")
	if not doc:
		return []
	return frappe.db.sql(
		"""select p.title as project_title, p.name as project_id, p.status as project_status,
			p.irb_cycle as irb_cycle, p.modified as last_updated
		from tabStudent as s
		join `tabStudent Project Mapping` as sp on sp.student = s.name
		join `tabIRB Project` as p on sp.irb_project = p.name
		where s.system_user = %(system_user)s
		and (sp.status = 'active' or p.status = 'Approved')
		order by p.modified desc""",
		{"system_user": doc.system_user},
		as_dict=True,
	)


@frappe.whitelist()
def get_mentor_projects(bucket="pending"):
	"""bucket: 'pending' | 'unapproved' | 'approved'. Mirrors Mentor's
	Pending Worklist / All (Un-)Approved Mentor Projects reports."""
	doc = get_logged_in_doc("Faculty Mentor")
	if bucket == "pending":
		clause = "and p.status = %(status)s"
		return _role_scoped_projects("faculty_mentor", doc, clause, {"status": MENTOR_PENDING_STATUS})
	if bucket == "approved":
		clause = "and p.status = 'Approved'"
		return _role_scoped_projects("faculty_mentor", doc, clause)
	# "unapproved" == "all still in progress" (matches All Mentor Projects / All
	# Un-approved Mentor Projects, which are functionally identical in the
	# original reports).
	clause = "and p.status != 'Approved'"
	return _role_scoped_projects("faculty_mentor", doc, clause)


@frappe.whitelist()
def get_primary_reviewer_projects(bucket="pending"):
	"""bucket: 'pending' | 'unapproved' | 'approved'."""
	doc = get_logged_in_doc("Primary Reviewer")
	if bucket == "pending":
		placeholders = {f"status{i}": s for i, s in enumerate(PRIMARY_REVIEWER_PENDING_STATUSES)}
		clause = "and p.status in (%s)" % ", ".join(f"%({k})s" for k in placeholders)
		return _role_scoped_projects("primary_reviewer", doc, clause, placeholders)
	if bucket == "approved":
		clause = "and p.status = 'Approved'"
		return _role_scoped_projects("primary_reviewer", doc, clause)
	clause = "and p.status != 'Approved'"
	return _role_scoped_projects("primary_reviewer", doc, clause)


@frappe.whitelist()
def get_secondary_reviewer_projects(bucket="pending"):
	"""bucket: 'pending' | 'unapproved' | 'approved'."""
	doc = get_logged_in_doc("Secondary Reviewer")
	if bucket == "pending":
		clause = "and p.status = %(status)s"
		return _role_scoped_projects(
			"secondary_reviewer", doc, clause, {"status": SECONDARY_REVIEWER_PENDING_STATUS}
		)
	if bucket == "approved":
		clause = "and p.status = 'Approved'"
		return _role_scoped_projects("secondary_reviewer", doc, clause)
	clause = "and p.status != 'Approved'"
	return _role_scoped_projects("secondary_reviewer", doc, clause)


@frappe.whitelist()
def get_my_pending_counts():
	"""Single aggregated payload of pending-item counts across whichever
	roles the current user actually holds — used to drive the role-routed
	Dashboard summary without firing one request per role.
	"""
	counts = {}

	mentor_doc = get_logged_in_doc("Faculty Mentor")
	if mentor_doc:
		counts["mentor_pending"] = len(
			_role_scoped_projects(
				"faculty_mentor", mentor_doc, "and p.status = %(status)s", {"status": MENTOR_PENDING_STATUS}
			)
		)

	pr_doc = get_logged_in_doc("Primary Reviewer")
	if pr_doc:
		placeholders = {f"status{i}": s for i, s in enumerate(PRIMARY_REVIEWER_PENDING_STATUSES)}
		clause = "and p.status in (%s)" % ", ".join(f"%({k})s" for k in placeholders)
		counts["primary_reviewer_pending"] = len(
			_role_scoped_projects("primary_reviewer", pr_doc, clause, placeholders)
		)

	sr_doc = get_logged_in_doc("Secondary Reviewer")
	if sr_doc:
		counts["secondary_reviewer_pending"] = len(
			_role_scoped_projects(
				"secondary_reviewer",
				sr_doc,
				"and p.status = %(status)s",
				{"status": SECONDARY_REVIEWER_PENDING_STATUS},
			)
		)

	student_doc = get_logged_in_doc("Student")
	if student_doc:
		counts["student_projects"] = len(get_student_projects())

	return counts
