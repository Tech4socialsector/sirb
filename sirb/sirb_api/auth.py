# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

import frappe

from sirb.utils import get_logged_in_doc


@frappe.whitelist()
def get_current_user():
	"""Session + SIRB-specific identity for the Vue auth store: standard
	Frappe roles plus which SIRB person records (Student/Faculty) resolve
	to this user, so the frontend can route to the right dashboard without
	re-deriving it from raw role strings.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Not logged in", frappe.AuthenticationError)

	roles = frappe.get_roles(user)
	student = get_logged_in_doc("Student")
	faculty = get_logged_in_doc("Faculty")

	return {
		"user": user,
		"full_name": frappe.utils.get_fullname(user),
		"roles": roles,
		"is_student": bool(student),
		"is_faculty": bool(faculty),
		"student_id": student.name if student else None,
		"faculty_id": faculty.name if faculty else None,
	}


@frappe.whitelist()
def get_my_profile():
	"""The caller's own Student / Faculty record for the Profile page.

	Faculty is readable only by System Manager, so the page's old
	frappe.client.get failed with 403 for every faculty user. This returns
	just the caller's own record (resolved from the session, never from a
	client-supplied name), with the few fields the page shows.
	"""
	if frappe.session.user == "Guest":
		frappe.throw("Not logged in", frappe.AuthenticationError)

	student = get_logged_in_doc("Student")
	faculty = get_logged_in_doc("Faculty")
	return {
		"student": {
			"name": student.name,
			"student_id": student.student_id,
			"full_name": student.full_name,
			"academic_year": student.academic_year,
		}
		if student
		else None,
		"faculty": {"name": str(faculty.name), "full_name": faculty.full_name} if faculty else None,
	}
