# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe


def after_install():
	"""Set Student Workspace as default for Student role users"""
	# Check if workspace exists
	if not frappe.db.exists("Workspace", "Student Workspace"):
		return
	
	# Get all users with Student role
	students = frappe.get_all(
		"Has Role",
		filters={"role": "Student", "parenttype": "User"},
		fields=["parent"]
	)
	
	# Set default workspace for each student user
	for student in students:
		user = student.parent
		try:
			frappe.db.set_value("User", user, "default_workspace", "Student Workspace")
		except Exception as e:
			frappe.log_error(f"Error setting default workspace for {user}: {str(e)}")
	
	frappe.db.commit()

