# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

# import frappe
from frappe.utils.nestedset import NestedSet


class AcademicOrganizationalUnit(NestedSet):
	def autoname(self):
		parent = self.parent_academic_organizational_unit
		own_value = self.ao_code

		if parent:
			self.name = f"{parent}-{own_value}"
		else:
			self.name = own_value
