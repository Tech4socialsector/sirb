# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Row-level access for IRB Project.

The Student / Faculty Mentor / Reviewer roles grant read+write on the
whole IRB Project doctype, so without these hooks any student could open
(and edit) every other student's proposal — and, through it, the private
files attached to it. A user may only access a project they're on:

- Student: has a Student Project Mapping to it (active or not, so an
  approved project stays visible to its students)
- Faculty: is its faculty mentor, primary reviewer or secondary reviewer
- System Manager / Administrator: every project

Frappe controller hooks can only narrow what role permissions allow,
never widen it.
"""

import frappe

UNRESTRICTED_ROLES = {"System Manager", "Administrator"}


def _unrestricted(user):
	return user == "Administrator" or bool(set(frappe.get_roles(user)) & UNRESTRICTED_ROLES)


def _faculty_ids(user):
	return frappe.get_all("Faculty", filters={"system_user": user}, pluck="name")


def _student_ids(user):
	return frappe.get_all("Student", filters={"system_user": user}, pluck="name")


def has_irb_project_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user
	if _unrestricted(user):
		return True
	if not doc.get("name") or (hasattr(doc, "is_new") and doc.is_new()):
		# Creation is governed by role permissions (only imports create them).
		return None

	faculty = {str(f) for f in _faculty_ids(user)}
	if faculty and {str(doc.get(f) or "") for f in ("faculty_mentor", "primary_reviewer", "secondary_reviewer")} & faculty:
		return True

	students = _student_ids(user)
	if students and frappe.db.exists("Student Project Mapping", {"irb_project": doc.name, "student": ("in", students)}):
		return True

	return False


def irb_project_query_conditions(user=None):
	"""Same rule for list/count queries (Desk list view, get_list, get_count)."""
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""

	conditions = []
	faculty = _faculty_ids(user)
	if faculty:
		ids = ", ".join(frappe.db.escape(str(f)) for f in faculty)
		conditions.append(
			f"(`tabIRB Project`.faculty_mentor in ({ids}) or `tabIRB Project`.primary_reviewer in ({ids})"
			f" or `tabIRB Project`.secondary_reviewer in ({ids}))"
		)
	students = _student_ids(user)
	if students:
		ids = ", ".join(frappe.db.escape(str(s)) for s in students)
		conditions.append(
			"`tabIRB Project`.name in (select sp.irb_project from `tabStudent Project Mapping` sp"
			f" where sp.student in ({ids}))"
		)
	return "(" + " or ".join(conditions) + ")" if conditions else "1=0"
