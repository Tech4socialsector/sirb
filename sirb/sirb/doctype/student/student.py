# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Student(Document):
	def before_save(self):
		user = frappe.get_doc("User", self.system_user)
		self.full_name = user.full_name

		
