# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url
from sirb.utils import send_email_if_configured

class StudentProjectMapping(Document):
	def before_save(self):
		pass
	def after_insert(self):
		#frappe.log_error("After Insert Triggered", "Debug")
		print("!!!")
		query = f'''select s.system_user as student_email, s.name as student_id, s.full_name as student_name,
			f.name as mentor_id, p.status as status, p.title as title,
			f.system_user as mentor_email, p.primary_reviewer as pr_id, 
			p.secondary_reviewer as sr_id 
			from tabStudent as s join `tabStudent Project Mapping` as sp join 
			`tabIRB Project` as p 
			join tabFaculty as f on s.name = sp.student and 
			sp.irb_project = p.name  and p.faculty_mentor=f.name where 
			p.name="{self.irb_project}"'''
		#frappe.log_error(query, "Debug")
		notification_info = frappe.db.sql(query, as_dict=1)
		print("NOTIFICATION INFO ", notification_info)
		if notification_info:
			student_name_list = []
			student_email_list = []
			for n in notification_info:
				student_name_list.append(n["student_name"])
				student_email_list.append(n["student_email"])
			# full_name is optional on Student; a blank one must not break the insert.
			student_names = ",".join(n for n in student_name_list if n)
			project_url = get_url(f"/sirb/projects/{self.irb_project}")
			params = {
				"project_status": notification_info[0]["status"],
				"project_name": notification_info[0]["title"],
				"student_names": student_names,
				"project_url": project_url,
			}
			print("SENDING EMAIL!!")
			print(params)
			print(student_email_list)
			#frappe.log_error(str(student_email_list), "Debug")
			send_email_if_configured("New IRB Project Template", params, student_email_list)
