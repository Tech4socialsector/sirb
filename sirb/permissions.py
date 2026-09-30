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


def project_membership(user, doc):
	"""How `user` is attached to `doc` — the same rule as the access check
	below: any Student Project Mapping (active or not, so it survives
	approval) or the project's mentor/reviewer fields."""
	faculty = {str(f) for f in _faculty_ids(user)}
	students = _student_ids(user)
	return {
		"is_student": bool(students)
		and bool(frappe.db.exists("Student Project Mapping", {"irb_project": doc.name, "student": ("in", students)})),
		"is_mentor": str(doc.get("faculty_mentor") or "") in faculty,
		"is_primary_reviewer": str(doc.get("primary_reviewer") or "") in faculty,
		"is_secondary_reviewer": str(doc.get("secondary_reviewer") or "") in faculty,
	}


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


# Field-level write rules on top of the doctype's permlevels. Those come
# from a user's global roles, so e.g. someone who reviews any project gets
# reviewer-level write on every project they can open — including ones they
# only mentor. These narrow each save to the user's role on THIS project.

# Only admins may reassign a project (bulk import sets them on creation).
ADMIN_ONLY_FIELDS = ("faculty_mentor", "primary_reviewer", "secondary_reviewer", "irb_unit", "irb_cycle")

PROJECT_ROLE_TO_ROLE = {
	"is_student": "Student",
	"is_mentor": "Faculty Mentor",
	"is_primary_reviewer": "Primary IRB Reviewer",
	"is_secondary_reviewer": "Secondary IRB Reviewer",
}


def _normalized(df, value):
	"""Compare values the way they're stored, so a client sending "" for a
	NULL (or "1" for 1) isn't mistaken for an edit."""
	from frappe.utils import cint, flt

	if value in (None, ""):
		return None
	if df.fieldtype in ("Int", "Check"):
		return cint(value)
	if df.fieldtype in ("Float", "Currency", "Percent"):
		return flt(value)
	return str(value)


def validate_project_field_writes(doc):
	"""Throw if a non-admin changed a field their role on this project
	doesn't allow. Imports, patches and system jobs are exempt."""
	from frappe.model import no_value_fields

	if doc.is_new() or doc.flags.ignore_permissions or doc.flags.script_created:
		return
	if frappe.flags.in_import or frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_install:
		return
	if _unrestricted(frappe.session.user):
		return

	before = doc.get_doc_before_save()
	if not before:
		return

	changed = [
		df
		for df in doc.meta.fields
		if df.fieldtype not in no_value_fields
		and _normalized(df, doc.get(df.fieldname)) != _normalized(df, before.get(df.fieldname))
	]
	if not changed:
		return

	reassigned = [df.label or df.fieldname for df in changed if df.fieldname in ADMIN_ONLY_FIELDS]
	if reassigned:
		frappe.throw(
			f"Only an administrator can change {', '.join(reassigned)}.",
			frappe.PermissionError,
			title="Not allowed",
		)

	# Assignments as saved — reassigning is admin-only, checked above.
	project_roles = project_membership(frappe.session.user, before)
	roles = {role for flag, role in PROJECT_ROLE_TO_ROLE.items() if project_roles.get(flag)}
	writable = {p.permlevel for p in doc.get_permissions() if p.role in roles and p.write}
	# permlevel 0 (status, attachments) is governed by the status workflow
	# and role permissions; only the role-specific levels are narrowed here.
	blocked = [df.label or df.fieldname for df in changed if df.permlevel and df.permlevel not in writable]
	if blocked:
		frappe.throw(
			f"Your role on this project doesn't allow editing: {', '.join(blocked[:5])}"
			+ (f" and {len(blocked) - 5} more" if len(blocked) > 5 else "")
			+ ". Reload the page and try again.",
			frappe.PermissionError,
			title="Not allowed",
		)


# Student records: the Student / Faculty Mentor roles can read (and write)
# the whole doctype, which exposed every student's email and let anyone
# re-point a Student at their own login — and so take over that student's
# projects, since project access follows Student.system_user.
STUDENT_ADMIN_ROLES = UNRESTRICTED_ROLES | {"Anchor"}


def _student_admin(user):
	return user == "Administrator" or bool(set(frappe.get_roles(user)) & STUDENT_ADMIN_ROLES)


def _faculty_project_students_sql(faculty_ids):
	ids = ", ".join(frappe.db.escape(str(f)) for f in faculty_ids)
	return (
		"select sp.student from `tabStudent Project Mapping` sp join `tabIRB Project` p on sp.irb_project = p.name"
		f" where p.faculty_mentor in ({ids}) or p.primary_reviewer in ({ids}) or p.secondary_reviewer in ({ids})"
	)


def has_student_permission(doc, ptype=None, user=None, debug=False):
	"""A student sees their own record; faculty see students on projects
	they mentor or review; Anchors and admins see all."""
	user = user or frappe.session.user
	if _student_admin(user):
		return True
	if not doc.get("name") or (hasattr(doc, "is_new") and doc.is_new()):
		return None
	if doc.get("system_user") == user:
		return True
	faculty = _faculty_ids(user)
	if faculty:
		return bool(frappe.db.sql(f"select 1 from ({_faculty_project_students_sql(faculty)}) t where t.student = %s", doc.name))
	return False


def student_query_conditions(user=None):
	user = user or frappe.session.user
	if _student_admin(user):
		return ""
	conditions = [f"`tabStudent`.system_user = {frappe.db.escape(user)}"]
	faculty = _faculty_ids(user)
	if faculty:
		conditions.append(f"`tabStudent`.name in ({_faculty_project_students_sql(faculty)})")
	return "(" + " or ".join(conditions) + ")"


def validate_student_write(doc):
	"""Only Anchors/admins (and the bulk upload they run) may create a
	Student or change which login and student ID it belongs to."""
	if doc.flags.ignore_permissions or frappe.flags.in_import or frappe.flags.in_patch or frappe.flags.in_migrate:
		return
	if frappe.flags.in_install or _student_admin(frappe.session.user):
		return
	if doc.is_new():
		frappe.throw("Only an administrator can create Student records.", frappe.PermissionError, title="Not allowed")
	for fieldname in ("system_user", "student_id"):
		if doc.has_value_changed(fieldname):
			frappe.throw(
				f"Only an administrator can change {doc.meta.get_label(fieldname)}.",
				frappe.PermissionError,
				title="Not allowed",
			)


def validate_student_delete(doc):
	if frappe.flags.in_patch or frappe.flags.in_migrate or _student_admin(frappe.session.user):
		return
	frappe.throw("Only an administrator can delete Student records.", frappe.PermissionError, title="Not allowed")
