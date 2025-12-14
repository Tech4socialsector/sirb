# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator


class Student(WebsiteGenerator):
	def before_save(self):
		user = frappe.get_doc("User", self.full_name)
		self.display_full_name = user.full_name
		for p in self.projects:
			project = frappe.get_doc("Project", p.project)
			if p.full_name:
				faculty = frappe.get_doc("Faculty", p.full_name)
				if faculty:
					user = frappe.get_doc("User", faculty.full_name)
					p.faculty_mentor_name = user.full_name
			# else:
			# 	project.status = "Awaiting Faculty mentor assignment"
			# 	project.save()
			# 	frappe.db.commit()
		
