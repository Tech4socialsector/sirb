# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url
from sirb.proposal_checks import format_issues, get_proposal_issues
from sirb.workflow import validate_status_change
from sirb.utils import set_mentor_and_reviewer_roles, send_email_if_configured

# Statuses in which the student is filling in or correcting the proposal.
STUDENT_DRAFT_STATUSES = (
	"Awaiting proposal completion by student",
	"Awaiting student correction for mentor feedback",
	"Awaiting student correction for reviewer feedback",
)


class ProposalIncompleteError(frappe.ValidationError):
	pass

class IRBProject(Document):
	def validate(self):
		if self.flags.script_created:
			# Bulk import (see api.py:import_student_irb_information) creates a bare
			# IRB Project with only irb_unit/irb_cycle/owner set; the student fills
			# in the rest later, so skip mandatory checks for that creation only.
			self.flags.ignore_mandatory = True
			return

		# Only the transitions the user's role on this project allows
		# (status is read-only in the form but not enforced by Frappe).
		validate_status_change(self)

		# Roles allowed to edit an existing IRB Project without filling the
		# mandatory fields (e.g. status/reviewer/mentor changes on a project
		# the student never finished). Add more roles here if needed later.
		MANDATORY_BYPASS_ROLES = {"System Manager", "Administrator"}

		is_admin_edit = not self.is_new() and set(frappe.get_roles()) & MANDATORY_BYPASS_ROLES
		if is_admin_edit:
			self.flags.ignore_mandatory = True
			return

		if self.is_new():
			# Not script-created: core mandatory validation runs as normal.
			if not self.i_hereby_confirm_the_above:
				frappe.throw("Please ensure that you have read the IRB policy and checked the student declaration in the \"Uploads & Declaration\" tab")
			return

		if self.status in STUDENT_DRAFT_STATUSES:
			# The student is still writing (or correcting) the proposal: let
			# them save partial progress. Completeness is enforced when they
			# submit, below.
			self.flags.ignore_mandatory = True
			return

		previous = self.get_doc_before_save()
		if previous and previous.status in STUDENT_DRAFT_STATUSES:
			# Leaving a student-editing status = the student is submitting.
			# Check every rule at once so they get the full list, not one
			# error per attempt.
			issues = get_proposal_issues(self)
			if issues:
				frappe.throw(format_issues(issues), exc=ProposalIncompleteError, title="Proposal incomplete")

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

	# def after_insert(self):
	# 	frappe.log_error("After Insert Triggered", "Debug")
	# 	print("!!!")
	# 	query = f'''select s.system_user as student_email, s.name as student_id, s.full_name as student_name,
	# 		f.name as mentor_id,
	# 		f.system_user as mentor_email, p.primary_reviewer as pr_id,
	# 		p.secondary_reviewer as sr_id
	# 		from tabStudent as s join `tabStudent Project Mapping` as sp join
	# 		`tabIRB Project` as p
	# 		join tabFaculty as f on s.name = sp.student and
	# 		sp.irb_project = p.name  and p.faculty_mentor=f.name where
	# 		p.name="{self.name}"'''
	# 	frappe.log_error(query, "Debug")
	# 	notification_info = frappe.db.sql(query, as_dict=1)
	# 	frappe.log_error(str(notification_info), "Debug")
	# 	print("NOTIFICATION INFO ", notification_info)
	# 	if notification_info:
	# 		params = {
	# 			"project_status": self.status,
	# 			"project_name": self.title,
	# 			"student_names": student_names
	# 		}
	# 		student_name_list = []
	# 		student_email_list = []
	# 		for n in notification_info:
	# 			student_name_list.append(n["student_name"])
	# 			student_email_list.append(n["student_email"])
	# 		student_names = ",".join(student_name_list)
	# 		if student_names[-1] == ',':
	# 			student_names = student_names[:-1]
	# 		print("SENDING EMAIL!!")
	# 		print(params)
	# 		print(student_email_list)
	# 		frappe.log_error(str(student_email_list), "Debug")
	# 		send_email_if_configured("New IRB Project Template", params, student_email_list)

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
					f.system_user as mentor_email, p.primary_reviewer as pr_id,
					p.secondary_reviewer as sr_id
					from tabStudent as s join `tabStudent Project Mapping` as sp join
					`tabIRB Project` as p
					join tabFaculty as f on s.name = sp.student and
					sp.irb_project = p.name  and p.faculty_mentor=f.name where
					p.name="{self.name}"''', as_dict=1
				)
				print("NOTIFICATION INFO ", notification_info)
				#[{'student_email': 'student1@apu.in', 'student_id': 17, 'mentor_id': 4, 'faculty_email': 'f1@apu.in', 'pr_id': '4', 'sr_id': None}]


				if notification_info:
					student_name_list = []
					student_email_list = []
					for n in notification_info:
						student_name_list.append(n["student_name"])
						student_email_list.append(n["student_email"])
					# full_name is optional on Student; a blank one must not break the save.
					student_names = ",".join(n for n in student_name_list if n)
					mentor_email = notification_info[0]["mentor_email"]
					faculty_recipient_list = []
					to_students = to_faculty = False
					print("Statis is ", self.status)
					if self.status == "Awaiting Faculty mentor approval":
						# recipient_list.append(frappe.get_doc("Faculty", notification_info[0]["mentor_id"]))
						faculty_recipient_list.append(mentor_email)
						template = "Awaiting Mentor Approval Template"
						to_faculty = True
						to_students = True
					elif self.status in ["Awaiting reviewer feedback to student", "Awaiting primary reviewer comments to secondary reviewer"]:
						if notification_info[0]["pr_id"]:
							pr_email = frappe.get_value("Faculty", notification_info[0]["pr_id"], "system_user")
							faculty_recipient_list.append(pr_email)
							to_faculty = True
					elif self.status in ["Awaiting secondary reviewer comments to primary reviewer"]:
						print("!!!!")
						if notification_info[0]["sr_id"]:
							sr_email = frappe.get_value("Faculty", notification_info[0]["sr_id"], "system_user")
							faculty_recipient_list.append(sr_email)
							to_faculty = True
					elif self.status == "Provisionally approved":
						template = "Project Provisionally Approved Template"
						faculty_recipient_list.append(mentor_email)
						to_students = True
						to_faculty = True
					elif self.status == "Approved":
						template = "Project Approved Template"
						faculty_recipient_list.append(mentor_email)
						to_students = True
						to_faculty = True
					elif self.status == "Awaiting student correction for reviewer feedback":
						template = "Student Correction For Reviewer Feedback Template"
						to_students = True
					elif self.status in ["Awaiting student correction for mentor feedback"]:
						template = "Student Correction For Mentor Feedback Template"
						to_students = True
					# print("Recipient list ", recipient_list)
					# Create a system notification
					project_url = get_url(f"/sirb/projects/{self.name}")
					params = {
						"project_status": self.status,
						"project_name": self.title,
						"student_names": student_names,
						"project_url": project_url,
					}
					if to_faculty:
						send_email_if_configured("Status Change Email Template", params, faculty_recipient_list)
					if to_students:
						send_email_if_configured(template, params, student_email_list)
					# for u in recipient_list:
					# 	notification = frappe.new_doc("Notification Log")
					# 	notification.subject = f"IRBProject \"{self.title}\" status has changed to \"{self.status}\""
					# 	#notification.email_content = f"The status of irb_project <b>{self.title}</b> for <b>{notification["full_name"]<b> was changed to <b>{self.status}</b>."
					# 	notification.for_user = u
					# 	notification.document_type = self.doctype
					# 	notification.document_name = self.name
					# 	notification.type = "Alert"
					# 	notification.from_user = frappe.session.user
					# 	notification.insert(ignore_permissions=True)
					# 	# Immediately push to UI (real-time popup)
					# 	frappe.publish_realtime(
					# 		"eval_js",
					# 		{"js": f"frappe.show_alert('Task {self.name} status changed to {self.status}');"},
					# 		user=u
					# 	)
		if self.status == "Approved":
			sp_mappings = frappe.get_all("Student Project Mapping", filters = {
				"irb_project": self.name,
				"status": "active"
			})
			# print("Mappings - ", sp_mappings)
			for sp in sp_mappings:
				# Closing the student's mapping is a system consequence of the
				# approval, not an edit by the approver — reviewers have no
				# write access to Student Project Mapping, which made "Grant
				# FINAL approval" fail with a PermissionError. Committing is left
				# to the request so a later failure can't leave it half-done.
				sp_doc = frappe.get_doc("Student Project Mapping", sp["name"])
				sp_doc.status = "inactive"
				sp_doc.flags.ignore_permissions = True
				sp_doc.save()

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








