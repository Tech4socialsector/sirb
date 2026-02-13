# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class IRBUnit(Document):
	def on_update(self):
		self.update_reviewer_roles()
		#self.revoke_roles_if_not_needed(None)

	def update_reviewer_roles(self):
		current_reviewer_faculty = [row.faculty_member for row in self.irb_committee_faculty_members]
		current_reviewer_faculty_users = []
		if current_reviewer_faculty:
			for crf in current_reviewer_faculty:
				faou_doc = frappe.get_doc("Faculty Academic Organizational Unit", crf)
				faculty_doc = frappe.get_doc("Faculty", faou_doc.faculty_member)
				crfu = frappe.get_doc("User", faculty_doc.system_user)
				crfu.add_roles("IRB Reviewer")
				current_reviewer_faculty_users.append(crfu)
		self.revoke_roles_if_not_needed()

	def revoke_roles_if_not_needed(self):
		result = frappe.db.sql(
			f'''
			select u.email from tabFaculty as f join tabUser as u join `tabIRB Unit` as irb_unit 
			join `tabIRB Faculty Grouping` as ifg join `tabFaculty Academic Organizational Unit` as faou
			on f.system_user=u.email and ifg.parent = irb_unit.name and ifg.faculty_member=faou.name 
			and faou.faculty_member = f.name 
			''', as_list=True
		)
		all_valid_reviewer_users = [e[0] for e in result]
		result = frappe.db.sql("select u.email from tabUser as u join tabFaculty as f where u.email=f.system_user", as_list = True)
		all_faculty_users = [e[0] for e in result]
		print(all_valid_reviewer_users, all_faculty_users)
		for u in all_faculty_users:
			if u not in all_valid_reviewer_users:
				print("Removing role for ", u)
				udoc = frappe.get_doc("User", u)
				udoc.remove_roles("IRB Reviewer")

