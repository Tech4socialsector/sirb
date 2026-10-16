# Copyright (c) 2026, Ram and Contributors
# See license.txt
"""Status-change side effects in IRBProject.on_change: who is e-mailed, and
Student Project Mappings following the project in and out of Approved."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from sirb.api import _get_irb_project_roles
from sirb.patches.v1_0 import reactivate_reverted_project_mappings
from sirb.sirb_api.worklists import get_mentor_projects
from sirb.workflow import APPROVED, FINAL_APPROVAL, PROVISIONAL, REVIEWER_FEEDBACK

# Dummy users from sirb.test_users (bench --site <site> execute sirb.test_users.create).
STUDENT = "sirb.student4@example.com"
MENTOR = "sirb.mentor@example.com"
PRIMARY = "sirb.primary@example.com"

SEND = "sirb.sirb.doctype.irb_project.irb_project.send_email_if_configured"


class TestStatusChange(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.mentor = frappe.db.get_value("Faculty", {"system_user": MENTOR})
		cls.primary = frappe.db.get_value("Faculty", {"system_user": PRIMARY})
		cls.student = frappe.db.get_value("Student", {"system_user": STUDENT})
		if not (cls.mentor and cls.primary and cls.student):
			raise cls.skipTest(cls, "run sirb.test_users.create first")
		cls.unit = frappe.db.get_value("IRB Project", {"faculty_mentor": cls.mentor}, "irb_unit")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _project(self, status, mentor=True):
		project = frappe.new_doc("IRB Project")
		project.update(
			{
				"title": "[TEST] status change",
				"irb_unit": self.unit,
				"project_domain": "Humans",
				"status": status,
				"faculty_mentor": self.mentor if mentor else None,
				"primary_reviewer": self.primary,
			}
		)
		project.set_new_name()
		project.set_user_and_timestamp()
		project.db_insert()
		mapping = frappe.new_doc("Student Project Mapping")
		mapping.update(
			{"student": self.student, "irb_project": project.name, "status": "inactive" if status == APPROVED else "active"}
		)
		mapping.set_new_name()
		mapping.set_user_and_timestamp()
		mapping.db_insert()
		return project.name

	def _move(self, name, status):
		"""Save a status change as Administrator; return the e-mails sent as
		{template: recipients}."""
		doc = frappe.get_doc("IRB Project", name)
		doc.status = status
		with patch(SEND) as send:
			doc.save()
		return {c.args[0]: c.args[2] for c in send.call_args_list}

	def _mapping_status(self, name):
		return frappe.get_all("Student Project Mapping", filters={"irb_project": name}, pluck="status")

	def test_resubmission_after_provisional_approval_emails_primary_reviewer(self):
		sent = self._move(self._project(PROVISIONAL), FINAL_APPROVAL)
		self.assertEqual(sent, {"Status Change Email Template": [PRIMARY]})

	def test_project_without_mentor_still_emails_reviewer(self):
		sent = self._move(self._project(PROVISIONAL, mentor=False), FINAL_APPROVAL)
		self.assertEqual(sent, {"Status Change Email Template": [PRIMARY]})

	def test_approval_still_emails_mentor_and_students(self):
		sent = self._move(self._project(FINAL_APPROVAL), APPROVED)
		self.assertEqual(sent["Status Update Email Template"], [MENTOR])
		self.assertEqual(sent["Project Approved Template"], [STUDENT])

	def test_moving_back_from_approved_reactivates_mappings(self):
		name = self._project(REVIEWER_FEEDBACK)
		self._move(name, APPROVED)
		self.assertEqual(self._mapping_status(name), ["inactive"])

		self._move(name, PROVISIONAL)
		self.assertEqual(self._mapping_status(name), ["active"])

		frappe.set_user(MENTOR)
		self.assertIn(name, [p.project_name for p in get_mentor_projects("unapproved")])
		self.assertTrue(_get_irb_project_roles(STUDENT, name)["is_student"])

	def test_patch_repairs_projects_already_moved_back(self):
		name = self._project(REVIEWER_FEEDBACK)
		self._move(name, APPROVED)
		# What a revert left behind before the fix: inactive mappings.
		frappe.db.set_value("IRB Project", name, "status", PROVISIONAL)
		frappe.get_doc(
			{
				"doctype": "Version",
				"ref_doctype": "IRB Project",
				"docname": str(name),
				"data": frappe.as_json({"changed": [["status", APPROVED, PROVISIONAL]]}),
			}
		).insert(ignore_permissions=True)
		untouched = self._project(REVIEWER_FEEDBACK)
		frappe.db.set_value("Student Project Mapping", {"irb_project": untouched}, "status", "inactive")

		reactivate_reverted_project_mappings.execute()

		self.assertEqual(self._mapping_status(name), ["active"])
		self.assertEqual(self._mapping_status(untouched), ["inactive"])
