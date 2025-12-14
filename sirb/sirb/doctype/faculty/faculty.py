# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator


class Faculty(WebsiteGenerator):
	def before_save(self):
		user = frappe.get_doc("User", self.full_name)
		self.display_full_name = user.full_name
