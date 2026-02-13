# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FacultyAcademicOrganizationalUnit(Document):
	def validate(self):
		f_name = ""
		ao_name = ""
		if self.faculty_member:
			f_name = frappe.db.get_value("Faculty", self.faculty_member, "full_name")
		if self.ao_unit:
			ao_name = frappe.db.get_value("Academic Organizational Unit", self.ao_unit, "ao_name")
		self.title = f"{f_name} ({ao_name})"
		#print(self.title)