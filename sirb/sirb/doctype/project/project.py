# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator


class Project(WebsiteGenerator):
	def before_save(self):
		# print("Before save")
		user = frappe.session.user
		fentries = frappe.db.get_all("Faculty", filters = {
			"full_name": user
		})

		roles = frappe.get_roles(user)
		# if fentries:
		# 	faculty = frappe.get_doc("Faculty", fentries[0]["name"])
		# 	if self.mentors_feedback:
		# 		for fmf in self.mentors_feedback:
		# 			if not fmf.facultys_role and "Faculty Mentor" in roles:
		# 				fmf.facultys_role = "Faculty Mentor"
		# 				fmf.facultys_name = faculty.display_full_name
		# 	#print("Reviewers are ", self.primary_reviewer, self.secondary_reviewer, fentries[0]["name"], self.primary_reviewer == fentries[0]["name"])						
		# 	if self.reviewers_comments:
		# 		for fmf in self.reviewers_comments:
		# 			if not fmf.facultys_role and ("Primarary Reviewer" in roles or "Secondary Reviewer in roles"):
		# 				if self.primary_reviewer == fentries[0]["name"]:
		# 					fmf.facultys_role = "Primary Reviewer"
		# 				else:
		# 					fmf.facultys_role = "Secondary Reviewer"
		# 				fmf.facultys_name = faculty.display_full_name
		# 	#print(self.reviewer_comments_for_student)
		# 	if self.reviewer_comments_for_student and len(self.reviewer_comments_for_student) > 5 and self.status not in ["Provisionally approved", "Approved"]:
		# 		#print("In!")
		# 		self.status = "Awaiting student correction for reviewer feedback"

	def on_change(self):
		# print("!!!!!")
		# print("On save")
		# print(frappe.session)
		# print(frappe.session.last_update)
		# print(self.name)
		doc_before = self.get_doc_before_save()
		if doc_before:
			if doc_before.status != self.status:
				# Status change so need to send a notification on status change

				notification_info = frappe.db.sql(
					f'''select s.full_name as student_email, s.name as student_id, s.display_full_name as student_name,
					f.name as mentor_id, 
					f.full_name as faculty_email, p.primary_reviewer as pr_id, p.secondary_reviewer as sr_id 
					from tabStudent as s join `tabStudent Project` 
					as sp join tabProject as p join tabFaculty as f on s.name = sp.parent and 
					sp.project = p.name  and sp.full_name=f.name and p.name="{self.name}"''', as_dict=1
				)
				#print(notification_info)
				#[{'student_email': 'student1@apu.in', 'student_id': 17, 'mentor_id': 4, 'faculty_email': 'f1@apu.in', 'pr_id': '4', 'sr_id': None}]


				if notification_info:
					recipient_list = []
					if self.status == "Awaiting Faculty mentor approval":
						recipient_list.append(frappe.get_doc("Faculty", notification_info[0]["mentor_id"]))
					elif self.status in ["Awaiting student correction for mentor feedback", "Awaiting student correction for reviewer feedback", "Provisionally approved", "Approved"]:
						recipient_list.append(frappe.get_doc("Student", notification_info[0]["student_id"]))
					elif self.status == "Awaiting reviewer feedback":
						if notification_info[0]["pr_id"]:
							recipient_list.append(frappe.get_doc("Faculty", notification_info[0]["pr_id"]))
						if notification_info[0]["sr_id"]:
							recipient_list.append(frappe.get_doc("Faculty", notification_info[0]["sr_id"]))

					
					# Create a system notification
					for u in recipient_list:
						notification = frappe.new_doc("Notification Log")
						notification.subject = f"Project \"{self.title}\" status has changed to \"{self.status}\""
						#notification.email_content = f"The status of project <b>{self.title}</b> for <b>{notification["full_name"]<b> was changed to <b>{self.status}</b>."
						notification.for_user = u
						notification.document_type = self.doctype
						notification.document_name = self.name
						notification.type = "Alert"
						notification.from_user = frappe.session.user
						notification.insert(ignore_permissions=True)
						# Immediately push to UI (real-time popup)
						frappe.publish_realtime(
							"eval_js",
							{"js": f"frappe.show_alert('Task {self.name} status changed to {self.status}');"},
							user=u
						)
		versions = frappe.get_all(
			"Version",
			filters={
				"ref_doctype": "Project",
				"docname": str(self.name)
			},
			fields=["name", "data", "creation"],
			order_by="creation"
		)
		# print("versions ", versions)
		
		changes_to_abstract = ""
		for v in versions:
			diff = frappe.parse_json(v.data).get("changed", [])
			# print(diff)
			if diff:
				for diff_instance in diff:
					if diff_instance[0] == "abstract":
						# print(diff_instance)
						#changes_to_abstract.append(f'"{diff_instance[1]}" changed to {diff_instance[2]}"')
						changes_to_abstract = f'"{diff_instance[1]}" changed to {diff_instance[2]}"'
		if changes_to_abstract:
			# print(changes_to_abstract)
			frappe.db.set_value("Project", self.name, "abstract_fc", changes_to_abstract)
			frappe.publish_realtime(
				event="reload_form",
				message={"doctype": "Project", "docname": self.name},
				after_commit=True
			)			



				


