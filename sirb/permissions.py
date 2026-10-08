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
- IRB Programme Manager: every project in their programmes (IRB Programme
  Access), to reassign the mentor/reviewers and set the status
- System Manager / Administrator: every project

Frappe controller hooks can only narrow what role permissions allow,
never widen it.
"""

import frappe

from sirb.sirb.doctype.irb_programme_access.irb_programme_access import (
	PROGRAMME_MANAGER_ROLE,
	get_viewer_irb_units,
)

UNRESTRICTED_ROLES = {"System Manager", "Administrator"}

# What a programme manager may change on their programmes' projects — the
# same fields an administrator edits on Project Details. Nothing else.
PROGRAMME_MANAGER_FIELDS = ("status", "faculty_mentor", "primary_reviewer", "secondary_reviewer")


def _unrestricted(user):
	return user == "Administrator" or bool(set(frappe.get_roles(user)) & UNRESTRICTED_ROLES)


def _faculty_ids(user):
	return frappe.get_all("Faculty", filters={"system_user": user}, pluck="name")


def _student_ids(user):
	return frappe.get_all("Student", filters={"system_user": user}, pluck="name")


def _managed_irb_units(user):
	if PROGRAMME_MANAGER_ROLE not in frappe.get_roles(user):
		return []
	return get_viewer_irb_units(user)


def manages_project(user, doc):
	"""True if `user` manages `doc` as an IRB Programme Manager: it belongs
	to one of their programmes and they aren't one of its students (no one
	may override the workflow on their own project). Pass the doc as saved,
	so the check can't follow an unsaved irb_unit change."""
	unit = doc.get("irb_unit")
	if not unit or unit not in _managed_irb_units(user):
		return False
	students = _student_ids(user)
	if students and doc.get("name"):
		return not frappe.db.exists("Student Project Mapping", {"irb_project": doc.name, "student": ("in", students)})
	return True


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

	# Programme managers: projects in their programmes, judged by the saved
	# irb_unit so an unsaved change can't move a project into reach.
	managed = _managed_irb_units(user)
	if managed and frappe.db.get_value("IRB Project", doc.name, "irb_unit") in managed:
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
	managed = _managed_irb_units(user)
	if managed:
		ids = ", ".join(frappe.db.escape(str(u)) for u in managed)
		conditions.append(f"`tabIRB Project`.irb_unit in ({ids})")
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


def _project_role_write_levels(doc, project_roles):
	roles = {role for flag, role in PROJECT_ROLE_TO_ROLE.items() if project_roles.get(flag)}
	return {p.permlevel for p in doc.get_permissions() if p.role in roles and p.write}


def writable_permlevels(doc, user=None):
	"""Permlevels whose fields a save by `user` on `doc` keeps: their global
	roles must allow it (Frappe resets the rest) and, for non-admins, so must
	their role on this project (validate_project_field_writes). Level 0 is
	governed by the status workflow instead."""
	user = user or frappe.session.user
	levels = set(doc.get_permlevel_access("write"))
	if _unrestricted(user):
		return levels
	allowed = _project_role_write_levels(doc, project_membership(user, doc)) | {0}
	return levels & allowed


def _normalized(df, value):
	"""Compare values the way they're stored, so a client sending "" for a
	NULL (or "1" for 1, or a browser's \n line endings for stored \r\n)
	isn't mistaken for an edit."""
	from frappe.utils import cint, flt

	if value in (None, ""):
		return None
	if df.fieldtype in ("Int", "Check"):
		return cint(value)
	if df.fieldtype in ("Float", "Currency", "Percent"):
		return flt(value)
	return str(value).replace("\r\n", "\n")


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

	# Programme managers may change the status / mentor / reviewers of their
	# programmes' projects; anything else falls through to the checks below.
	is_manager = manages_project(frappe.session.user, before)
	if is_manager:
		# Fetch-from fields (e.g. num_reviewers <- irb_unit) are re-copied by
		# Frappe on every save, overwriting anything the client sent, so a
		# change there is the linked record's, not the manager's.
		changed = [
			df
			for df in changed
			if df.fieldname not in PROGRAMME_MANAGER_FIELDS
			and not (df.fetch_from and not df.fetch_if_empty and doc.get(df.fetch_from.split(".")[0]))
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
	if is_manager and not any(project_roles.values()):
		# The manager role writes permlevel 0, where most proposal answers
		# live; without a role on the project, those stay the student's.
		frappe.throw(
			"As a programme manager you can only change the status, mentor and reviewers.",
			frappe.PermissionError,
			title="Not allowed",
		)
	writable = _project_role_write_levels(doc, project_roles)
	# permlevel 0 (status, attachments) is governed by the status workflow
	# and role permissions; only the role-specific levels are narrowed here.
	blocked = [df for df in changed if df.permlevel and df.permlevel not in writable]
	if blocked:
		# Put those fields back and save the rest, as Frappe itself does for
		# permlevels a user can't write. Throwing here discarded a reviewer's
		# whole save when Desk let them type into a field their global roles
		# allow (e.g. a reviewer who also has the Student role) but their
		# role on this project doesn't.
		for df in blocked:
			doc.set(df.fieldname, before.get(df.fieldname))
		labels = [df.label or df.fieldname for df in blocked]
		frappe.msgprint(
			"Your other changes were saved. These weren't, because your role on this project doesn't allow "
			f"editing them: {', '.join(labels[:5])}" + (f" and {len(labels) - 5} more" if len(labels) > 5 else "") + ".",
			title="Some changes not saved",
			indicator="orange",
		)


# Field-level read rules, per project. Like the write rules above, the
# doctype's read permlevels come from global roles (a faculty member who
# reviews any project reads reviewer-level fields on every project they can
# open), so these narrow what a user is shown on THIS project. Applied to
# Desk (IRBProject.apply_fieldlevel_read_permissions, sirb.overrides)
# and to the Vue page's API (sirb.sirb_api.project).

# Who reviews the project, and who mentors it.
REVIEWER_IDENTITY_FIELDS = ("primary_reviewer", "secondary_reviewer")
MENTOR_IDENTITY_FIELDS = ("faculty_mentor",)
# What the reviewers write: feedback to the student (_rf) and the notes they
# exchange between themselves (_prn/_srn).
REVIEWER_COMMENT_FIELDS = (
	"reviewers_comments_to_student",
	"primary_reviewers_comments_to_secondary_reviewer",
	"secondary_reviewers_comments_to_primary_reviewer",
)
REVIEWER_COMMENT_SUFFIXES = ("_rf", "_prn", "_srn")
# Reviewer-only fields a student may not see. Feedback addressed to them
# (_rf, reviewers_comments_to_student) is theirs to read.
STUDENT_HIDDEN_FIELDS = (
	*REVIEWER_IDENTITY_FIELDS,
	"num_reviewers",
	"primary_reviewers_comments_to_secondary_reviewer",
	"secondary_reviewers_comments_to_primary_reviewer",
	"mentor_comments_to_reviewers",
)
STUDENT_HIDDEN_SUFFIXES = ("_prn", "_srn")


def hidden_project_fields(doc, user=None):
	"""Fieldnames of `doc` that `user` may not see:

	- its students: who the reviewers are and the reviewers' internal notes
	- its faculty mentor: who the reviewers are and everything they write
	- its reviewers: who the faculty mentor is (not what the mentor writes)

	Admins and its programme managers (who assign mentors and reviewers)
	see everything. Pass the doc as saved, so membership can't follow an
	unsaved reassignment."""
	user = user or frappe.session.user
	if _unrestricted(user) or manages_project(user, doc):
		return set()
	membership = project_membership(user, doc)
	if membership["is_primary_reviewer"] or membership["is_secondary_reviewer"]:
		if membership["is_mentor"]:
			return set()
		names, suffixes = MENTOR_IDENTITY_FIELDS, ()
	elif membership["is_mentor"]:
		names, suffixes = REVIEWER_IDENTITY_FIELDS + REVIEWER_COMMENT_FIELDS, REVIEWER_COMMENT_SUFFIXES
	elif membership["is_student"]:
		names, suffixes = STUDENT_HIDDEN_FIELDS, STUDENT_HIDDEN_SUFFIXES
	else:
		return set()
	return {
		df.fieldname
		for df in doc.meta.fields
		if df.fieldname in names or df.fieldname.endswith(suffixes)
	}


def restore_hidden_project_fields(doc):
	"""Put back the stored value of every field the saving user may not see.
	Desk leaves those fields out of the form (they come back empty on save),
	and such a user has no business changing them anyway — even when their
	global roles would let them write that permlevel."""
	if doc.is_new():
		return
	before = doc.get_doc_before_save()
	if not before:
		return
	for fieldname in hidden_project_fields(before):
		doc.set(fieldname, before.get(fieldname))


# Shown instead of a name to those who may not know who it is.
REVIEWER_LABEL = "IRB Reviewer"
MENTOR_LABEL = "Faculty Mentor"
REVIEWER_ROLES = {"Primary IRB Reviewer", "Secondary IRB Reviewer"}


def person_masker(doc):
	"""Maps a user id (e.g. who made a change) to what the current user is
	shown on `doc`, as saved, following hidden_project_fields: anyone
	holding a reviewer role becomes REVIEWER_LABEL for those who may not see
	the reviewers, and the project's mentor becomes MENTOR_LABEL for those
	who may not see the mentor. Admins and the viewer are shown as-is."""
	hidden = hidden_project_fields(doc)
	mask_reviewers = any(f in hidden for f in REVIEWER_IDENTITY_FIELDS)
	mask_mentor = any(f in hidden for f in MENTOR_IDENTITY_FIELDS)
	mentor_user = doc.get("faculty_mentor") and frappe.db.get_value("Faculty", doc.faculty_mentor, "system_user")
	cache = {}

	def mask(user):
		if not user or user == frappe.session.user:
			return user
		if user == mentor_user:
			return MENTOR_LABEL if mask_mentor else user
		if not mask_reviewers:
			return user
		if user not in cache:
			cache[user] = not _unrestricted(user) and bool(REVIEWER_ROLES & set(frappe.get_roles(user)))
		return REVIEWER_LABEL if cache[user] else user

	return mask


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
