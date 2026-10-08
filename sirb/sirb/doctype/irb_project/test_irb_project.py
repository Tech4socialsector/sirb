# Copyright (c) 2025, Ram and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from sirb import overrides
from sirb.permissions import hidden_project_fields, hidden_project_fields_by_name, mask_project_rows
from sirb.workflow import REVIEWER_FEEDBACK, STUDENT_FIX_REVIEWER, validate_feedback_for_student

# Dummy users from sirb.test_users (bench --site <site> execute sirb.test_users.create).
STUDENT = "sirb.student@example.com"
MENTOR = "sirb.mentor@example.com"
PRIMARY = "sirb.primary@example.com"
SECONDARY = "sirb.secondary@example.com"


class TestIRBProject(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		people = {u: frappe.db.get_value("Faculty", {"system_user": u}) for u in (MENTOR, PRIMARY, SECONDARY)}
		student = frappe.db.get_value("Student", {"system_user": STUDENT})
		if not all(people.values()) or not student:
			raise cls.skipTest(cls, "run sirb.test_users.create first")
		cls.unit = frappe.db.get_value("IRB Project", {"faculty_mentor": people[MENTOR]}, "irb_unit")

		project = frappe.new_doc("IRB Project")
		project.update(
			{
				"title": "[TEST] visibility",
				"irb_unit": cls.unit,
				"project_domain": "Humans",
				"status": REVIEWER_FEEDBACK,
				"faculty_mentor": people[MENTOR],
				"primary_reviewer": people[PRIMARY],
				"secondary_reviewer": people[SECONDARY],
				"heq_s12_rf": "feedback for the student",
				"heq_s12_prn": "note to the secondary reviewer",
				"heq_s12_mf": "mentor feedback",
			}
		)
		project.set_new_name()
		project.db_insert()
		mapping = frappe.new_doc("Student Project Mapping")
		mapping.update({"student": student, "irb_project": project.name, "status": "active"})
		mapping.set_new_name()
		mapping.db_insert()
		cls.project = str(project.name)
		cls.people = {u: str(f) for u, f in people.items()}

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		super().tearDownClass()

	def tearDown(self):
		frappe.set_user("Administrator")

	def _row(self):
		return frappe._dict(
			frappe.get_all(
				"IRB Project",
				filters={"name": self.project},
				fields=["name", "title", "faculty_mentor", "primary_reviewer", "heq_s12_rf", "heq_s12_prn"],
			)[0]
		)

	def test_list_rows_follow_the_form_rule(self):
		for user in (STUDENT, MENTOR, PRIMARY, SECONDARY):
			frappe.set_user(user)
			doc = frappe.get_doc("IRB Project", self.project)
			self.assertEqual(hidden_project_fields_by_name([self.project])[self.project], hidden_project_fields(doc), user)

	def test_reviewer_does_not_see_mentor_in_lists(self):
		frappe.set_user(PRIMARY)
		row = mask_project_rows([self._row()])[0]
		self.assertIsNone(row.faculty_mentor)
		self.assertEqual(row.primary_reviewer, self.people[PRIMARY])
		self.assertEqual(row.title, "[TEST] visibility")

	def test_mentor_does_not_see_reviewers_in_lists(self):
		frappe.set_user(MENTOR)
		keys = ["name", "faculty_mentor", "primary_reviewer", "heq_s12_rf", "heq_s12_prn"]
		row = self._row()
		masked = mask_project_rows([tuple(row[k] for k in keys)], keys)[0]
		self.assertEqual(masked, [row.name, self.people[MENTOR], None, None, None])

	def test_student_sees_feedback_not_reviewers(self):
		frappe.set_user(STUDENT)
		row = mask_project_rows([self._row()])[0]
		self.assertEqual(row.heq_s12_rf, "feedback for the student")
		self.assertIsNone(row.heq_s12_prn)
		self.assertIsNone(row.primary_reviewer)

	def test_rows_without_name_hide_by_any_project(self):
		frappe.set_user(PRIMARY)
		rows = mask_project_rows([{"faculty_mentor": self.people[MENTOR], "title": "x"}])
		self.assertEqual(rows, [{"faculty_mentor": None, "title": "x"}])

	def test_admin_sees_everything(self):
		row = self._row()
		self.assertEqual(mask_project_rows([dict(row)])[0], dict(row))

	def test_get_value(self):
		frappe.set_user(PRIMARY)
		self.assertEqual(overrides.client_get_value("IRB Project", "faculty_mentor", self.project), {"faculty_mentor": None})
		self.assertIsNone(overrides.client_get_value("IRB Project", "faculty_mentor", self.project, as_dict=False))
		self.assertEqual(overrides.client_get_value("IRB Project", "title", self.project), {"title": "[TEST] visibility"})
		value = overrides.client_get_value(
			"IRB Project", json.dumps(["title", "faculty_mentor"]), json.dumps({"name": self.project})
		)
		self.assertEqual(value, {"title": "[TEST] visibility", "faculty_mentor": None})
		frappe.set_user(MENTOR)
		self.assertEqual(
			overrides.client_get_value("IRB Project", "faculty_mentor", self.project, as_dict=False), self.people[MENTOR]
		)

	def test_group_by_mentor_hidden_from_reviewer(self):
		frappe.set_user(PRIMARY)
		self.assertEqual(overrides.get_group_by_count("IRB Project", "[]", "faculty_mentor"), [])

	def _send_back(self, **values):
		doc = frappe.get_doc("IRB Project", self.project)
		doc._doc_before_save = frappe.copy_doc(doc)
		doc._doc_before_save.name = doc.name
		doc.update({"heq_s12_rf": "", "reviewers_comments_to_student": "", **values})
		doc.status = STUDENT_FIX_REVIEWER
		validate_feedback_for_student(doc)

	def test_send_back_needs_feedback_the_student_can_read(self):
		frappe.set_user(PRIMARY)
		with self.assertRaises(frappe.ValidationError):
			self._send_back()
		# Notes to the other reviewer don't count: the student can't read them.
		with self.assertRaises(frappe.ValidationError):
			self._send_back(heq_s12_prn="only a note")
		self._send_back(heq_s12_rf="please clarify")
		self._send_back(reviewers_comments_to_student="see the general comments")

	def test_admin_may_send_back_without_feedback(self):
		self._send_back()
