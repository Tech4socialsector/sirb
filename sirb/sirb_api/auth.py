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
