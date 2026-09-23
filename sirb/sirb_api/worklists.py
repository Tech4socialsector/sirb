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

# Approving a project flips its Student Project Mapping rows to "inactive"
# (see IRBProject.on_change), so a plain `sp.status = 'active'` filter made
# every "Approved" worklist tab permanently empty. Same condition as the
# student list and the Anchor reports.
ACTIVE_OR_APPROVED = "(sp.status = 'active' or p.status = 'Approved')"

# One row per project: a group project has several Student Project Mapping
# rows, so members are aggregated rather than returned as duplicate rows.
PROJECT_ROW_FIELDS = """
	select min(s.name) as student_id,
		group_concat(distinct s.full_name order by s.full_name separator ', ') as student_name,
		count(distinct s.name) as student_count,
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
		+ " where f.system_user = %(system_user)s and " + ACTIVE_OR_APPROVED + " " + status_clause
		+ " group by p.name order by p.modified desc"
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
			p.irb_cycle as irb_cycle, p.modified as last_updated,
			(select count(distinct m.student) from `tabStudent Project Mapping` as m
				where m.irb_project = p.name) as student_count,
			(select group_concat(distinct o.full_name order by o.full_name separator ', ')
				from `tabStudent Project Mapping` as m join tabStudent as o on o.name = m.student
				where m.irb_project = p.name and o.name != s.name) as teammates
		from tabStudent as s
		join `tabStudent Project Mapping` as sp on sp.student = s.name
		join `tabIRB Project` as p on sp.irb_project = p.name
		where s.system_user = %(system_user)s
		and (sp.status = 'active' or p.status = 'Approved')
		group by p.name
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
		student_projects = get_student_projects()
		counts["student_projects"] = len(student_projects)
		counts["student_group_projects"] = sum(1 for p in student_projects if p.student_count > 1)

	return counts


# (dashboard key, Frappe role that grants it, get_logged_in_doc key,
#  IRB Project field, pending statuses, worklist route). The Frappe role and
# the get_logged_in_doc key differ for reviewers ("Primary IRB Reviewer" vs
# "Primary Reviewer"), so both are listed.
DASHBOARD_ROLES = [
	("mentor", "Faculty Mentor", "Faculty Mentor", "faculty_mentor", [MENTOR_PENDING_STATUS], "/sirb/review/mentor"),
	(
		"primary_reviewer",
		"Primary IRB Reviewer",
		"Primary Reviewer",
		"primary_reviewer",
		PRIMARY_REVIEWER_PENDING_STATUSES,
		"/sirb/review/primary",
	),
	(
		"secondary_reviewer",
		"Secondary IRB Reviewer",
		"Secondary Reviewer",
		"secondary_reviewer",
		[SECONDARY_REVIEWER_PENDING_STATUS],
		"/sirb/review/secondary",
	),
]


def _role_bucket_counts(role_field, doc, pending_statuses):
	"""Pending / in-progress / approved counts in one query. Same joins and
	scoping as _role_scoped_projects, so each number equals the length of
	the matching worklist tab."""
	placeholders = {f"status{i}": s for i, s in enumerate(pending_statuses)}
	pending_in = ", ".join(f"%({k})s" for k in placeholders)
	row = frappe.db.sql(
		f"""select
			count(distinct case when p.status in ({pending_in}) then p.name end) as pending,
			count(distinct case when p.status != 'Approved' then p.name end) as in_progress,
			count(distinct case when p.status = 'Approved' then p.name end) as approved
		from tabStudent as s
		join `tabStudent Project Mapping` as sp on sp.student = s.name
		join `tabIRB Project` as p on sp.irb_project = p.name
		join tabFaculty as f on p.{role_field} = f.name
		where f.system_user = %(system_user)s and {ACTIVE_OR_APPROVED}""",
		{"system_user": doc.system_user, **placeholders},
		as_dict=True,
	)[0]
	return {k: int(row[k] or 0) for k in ("pending", "in_progress", "approved")}


@frappe.whitelist()
def get_my_dashboard(recent_limit=5):
	"""Everything the Dashboard shows, in one request: for each mentor /
	reviewer role the user holds, the three worklist-tab counts plus their
	most recently updated in-progress projects (each flagged with whether
	it is waiting on *this* user), and the student's own project counts.
	"""
	recent_limit = max(1, min(int(recent_limit or 5), 20))
	user_roles = set(frappe.get_roles())
	roles = []

	for key, role, doc_key, field, pending_statuses, route in DASHBOARD_ROLES:
		if role not in user_roles:
			continue
		doc = get_logged_in_doc(doc_key)
		if not doc:
			continue
		recent = _role_scoped_projects(field, doc, "and p.status != 'Approved'")
		for row in recent:
			row["needs_action"] = row.project_status in pending_statuses
		# Projects waiting on this user first; the stable sort keeps the
		# query's most-recently-updated order within each group.
		recent = sorted(recent, key=lambda r: not r["needs_action"])[:recent_limit]
		roles.append({"key": key, "route": route, "counts": _role_bucket_counts(field, doc, pending_statuses), "recent": recent})

	student = None
	if get_logged_in_doc("Student"):
		projects = get_student_projects()
		student = {
			"total": len(projects),
			"group": sum(1 for p in projects if (p.student_count or 0) > 1),
			"approved": sum(1 for p in projects if p.project_status == "Approved"),
		}

	return {"roles": roles, "student": student}
