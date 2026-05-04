# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from sirb.utils import set_mentor_and_reviewer_roles

class IRBProject(Document):
	def validate(self):
        # Skip validation for new documents
		if not self.is_new():
			if self.project_domain == "-- Select --":
				frappe.throw("Please select a valid IRB project domain.")
			elif self.project_domain == "Humans":
				if self.minor_participants == "-- Select --":
					frappe.throw("Please select a valid answer for 4. Minors check")
				if self.will_data_be_gathered_through_digital_means == "-- Select --":
					frappe.throw("Please select a valid answer for 13.Gathering of Audio, Photographic and Video Data")
		else:
			# Ignore mandatory checks since it is created by a script.
			self.flags.ignore_mandatory = True

	def before_save(self):
		# print("Before save")
		user = frappe.session.user
		fentries = frappe.db.get_all("Faculty", filters = {
			"system_user": user
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
		set_mentor_and_reviewer_roles()
		doc_before = self.get_doc_before_save()
		if doc_before:
			if doc_before.status != self.status:
				# Status change so need to send a notification on status change

				notification_info = frappe.db.sql(
					f'''select s.system_user as student_email, s.name as student_id, s.full_name as student_name,
					f.name as mentor_id, 
					f.system_user as faculty_email, p.primary_reviewer as pr_id, 
					p.secondary_reviewer as sr_id 
					from tabStudent as s join `tabStudent Project Mapping` as sp join 
					`tabIRB Project` as p 
					join tabFaculty as f on s.name = sp.student and 
					sp.irb_project = p.name  and p.faculty_mentor=f.name where 
					sp.status="active" and p.name="{self.name}"''', as_dict=1
				)
				print("NOTIFICATION INFO ", notification_info)
				#[{'student_email': 'student1@apu.in', 'student_id': 17, 'mentor_id': 4, 'faculty_email': 'f1@apu.in', 'pr_id': '4', 'sr_id': None}]


				if notification_info:
					recipient_list = []
					to_student = to_mentor = to_pr = to_sr = False
					print("Statis is ", self.status)
					if self.status == "Awaiting Faculty mentor approval":
						print("!")
						faculty_email = notification_info[0]["faculty_email"]
						# recipient_list.append(frappe.get_doc("Faculty", notification_info[0]["mentor_id"]))
						recipient_list.append(faculty_email)
						to_mentor = True
					elif self.status in ["Awaiting student correction for mentor feedback", "Awaiting student correction for reviewer feedback", "Provisionally approved", "Approved"]:
						print("!!")
						student_email = notification_info[0]["student_email"]
						#recipient_list.append(frappe.get_doc("Student", notification_info[0]["student_id"]))
						recipient_list.append(student_email)
						to_student = True
					elif self.status in ["Awaiting reviewer feedback to student", "Awaiting primary reviewer comments"]:
						print("!!!")
						if notification_info[0]["pr_id"]:
							pr_email = frappe.get_value("Faculty", notification_info[0]["pr_id"], "system_user")
							recipient_list.append(pr_email)
							to_pr = True
					elif self.status in ["Awaiting secondary reviewer comments"]:
						print("!!!!")
						if notification_info[0]["sr_id"]:
							sr_email = frappe.get_value("Faculty", notification_info[0]["sr_id"], "system_user")
							recipient_list.append(sr_email)
							to_sr = True
					

					print("Recipient list ", recipient_list)
					# Create a system notification
					params = {
						"project_status": self.status,
						"project_name": self.title,
						"student_name": notification_info[0]["student_name"]
					}
					send_email_if_configured("Status Change Email Template", params, recipient_list)
					for u in recipient_list:
						notification = frappe.new_doc("Notification Log")
						notification.subject = f"IRBProject \"{self.title}\" status has changed to \"{self.status}\""
						#notification.email_content = f"The status of irb_project <b>{self.title}</b> for <b>{notification["full_name"]<b> was changed to <b>{self.status}</b>."
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
				"ref_doctype": "IRB Project",
				"docname": str(self.name)
			},
			fields=["name", "data", "creation"],
			order_by="creation"
		)
		#print("versions ", versions)
		# parent_fields = ["consent_form_attachment", "abstract"]
		# field_changes = False
		# for pf in parent_fields:
		# 	changes = ""
		# 	for v in versions:
		# 		diff = frappe.parse_json(v.data).get("changed", [])
		# 		# print(diff)
		# 		if diff:
		# 			for diff_instance in diff:
		# 				#print(diff_instance[0])
		# 				if diff_instance[0] == pf:
		# 					changes = f'"{diff_instance[1]}" changed to {diff_instance[2]}"'
		# 	if changes:
		# 		field_changes = True
		# 		#print("CHANGED!! ", changes)
		# 		frappe.db.set_value("IRB Project", self.name, f"{pf}_fc", changes)
		# if field_changes:
		# 	frappe.publish_realtime(
		# 		event="reload_form",
		# 		message={"doctype": "IRB Project", "docname": self.name},
		# 		after_commit=True
		# 	)


def send_email_if_configured(email_template, params, recipient_list):
	# Fetch the default outgoing email account
	default_email_account = frappe.db.get_value("Email Account", {
		"default_outgoing": 1,
		"enable_outgoing": 1
	}, "name")

	# Check if an account exists
	if default_email_account:
		email_template_doc = frappe.get_doc("Email Template", email_template)
		rendered_content = frappe.render_template(email_template_doc.response_, params)
		rendered_subject = frappe.render_template(email_template_doc.subject, params)
		frappe.sendmail(
			subject = rendered_subject,
			content = rendered_content,
			recipients=recipient_list,
			delayed=False
		)
	else:
		frappe.logger().info("Default email account not set")


        

				


