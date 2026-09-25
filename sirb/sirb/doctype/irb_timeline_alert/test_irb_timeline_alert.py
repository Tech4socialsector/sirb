# Copyright (c) 2026, Ram and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from sirb.sirb_api.alert_templates import DEFAULT_TEMPLATES, ensure_default_templates
from sirb.sirb_api.timeline_alerts import (
	_render,
	_sample_row,
	compute_next_run,
	normalize_editor_html,
	normalize_filters,
	unknown_variables,
)


class TestIRBTimelineAlert(FrappeTestCase):
	def test_once(self):
		self.assertEqual(compute_next_run("Once", "2026-01-01 10:00", after="2026-01-01 09:00"), get_datetime("2026-01-01 10:00"))
		self.assertIsNone(compute_next_run("Once", "2026-01-01 10:00", after="2026-01-01 10:00"))

	def test_interval_skips_missed_slots(self):
		# Scheduler was down for days: next slot is the next future one, not a replay.
		self.assertEqual(compute_next_run("Daily", "2026-01-01 10:00", after="2026-01-05 10:00"), get_datetime("2026-01-06 10:00"))
		self.assertEqual(compute_next_run("Weekly", "2026-01-01 10:00", after="2026-01-08 10:00"), get_datetime("2026-01-15 10:00"))

	def test_end_date(self):
		self.assertIsNone(compute_next_run("Weekly", "2026-01-01 10:00", "2026-01-14", after="2026-01-08 10:00"))
		self.assertEqual(
			compute_next_run("Weekly", "2026-01-01 10:00", "2026-01-15", after="2026-01-08 10:00"), get_datetime("2026-01-15 10:00")
		)

	def test_monthly_does_not_drift(self):
		self.assertEqual(compute_next_run("Monthly", "2026-01-31 08:00", after="2026-02-01"), get_datetime("2026-02-28 08:00"))
		self.assertEqual(compute_next_run("Monthly", "2026-01-31 08:00", after="2026-02-28 08:00"), get_datetime("2026-03-31 08:00"))

	def test_normalize_filters(self):
		self.assertEqual(
			normalize_filters({"status": "Approved", "irb_unit": ["b", "a", "a", ""], "from_date": "x", "inactive_days": "7", "junk": 1}),
			{"status": ["Approved"], "irb_unit": ["a", "b"], "inactive_days": 7},
		)
		self.assertEqual(normalize_filters(""), {})
		for bad in ({"inactive_days": -1}, {"inactive_days": 99999}, "{not json"):
			with self.assertRaises(frappe.ValidationError):
				normalize_filters(bad)

	def test_editor_bullet_lists_become_real_lists(self):
		quill = (
			'<div class="ql-editor read-mode"><ol><li data-list="bullet"><span class="ql-ui"></span>a</li>'
			'<li data-list="bullet">b</li><li data-list="ordered">c</li></ol><p><a href="{{ project_url }}">go</a></p></div>'
		)
		self.assertEqual(
			normalize_editor_html(quill), '<ul><li>a</li><li>b</li></ul><ol><li>c</li></ol><p><a href="{{ project_url }}">go</a></p>'
		)
		plain = "<ul><li>a</li></ul><p>{{ student_name }}</p>"
		self.assertIs(normalize_editor_html(plain), plain)

	def test_unknown_variables(self):
		self.assertEqual(
			unknown_variables("Hi {{ studnet_name }}", "{{ doc.project_titel }} {{ doc.student_name }} {% for x in [1] %}{{ x }}{% endfor %}"),
			["studnet_name", "doc.project_titel"],
		)
		self.assertEqual(unknown_variables("{{ project_label }}", "{{ mentor_name or 'your mentor' }}"), [])

	def test_default_templates_are_clean_and_render(self):
		for tpl in DEFAULT_TEMPLATES:
			self.assertEqual(unknown_variables(tpl["subject"], tpl["response"]), [], tpl["name"])
			self.assertNotIn("<br>", tpl["response"], "Desk's editor splits <br> lines into paragraphs")
			from sirb.sirb_api.irb_timelines import SAMPLE_DEADLINE, uses_deadline_variables

			# The deadline template only renders with a linked activity.
			deadline = SAMPLE_DEADLINE if uses_deadline_variables(tpl["subject"], tpl["response"]) else None
			subject, body = _render(tpl["subject"], tpl["response"], _sample_row(), deadline)
			self.assertNotIn("{{", subject + body, tpl["name"])

	def test_seeding_never_overwrites_an_edited_template(self):
		name = DEFAULT_TEMPLATES[0]["name"]
		ensure_default_templates()
		frappe.db.set_value("Email Template", name, "subject", "Edited by a System Manager")
		self.assertNotIn(name, ensure_default_templates())
		self.assertEqual(frappe.db.get_value("Email Template", name, "subject"), "Edited by a System Manager")
		frappe.db.rollback()

	def test_specific_students_never_widen_to_everyone(self):
		self.assertEqual(
			normalize_filters({"mode": "students", "student": ["B", "A", "A", ""], "status": ["Approved"], "inactive_days": 9, "campus": ["X"]}),
			{"mode": "students", "student": ["A", "B"], "status": ["Approved"]},
		)
		for empty in ({"mode": "students"}, {"mode": "students", "student": []}, {"mode": "students", "student": [""]}):
			with self.assertRaises(frappe.ValidationError):
				normalize_filters(empty)
		with self.assertRaises(frappe.ValidationError):
			normalize_filters({"mode": "students", "student": [f"S{i}" for i in range(501)]})

	def test_timeline_rules(self):
		from sirb.sirb_api.irb_timelines import _when, parse_statuses, uses_deadline_variables

		self.assertEqual(parse_statuses('["Approved", "junk", "Awaiting proposal completion by student"]'),
			["Awaiting proposal completion by student", "Approved"])  # workflow order, junk dropped
		self.assertEqual([_when(d) for d in (0, 1, -1, 5, -3)], ["today", "tomorrow", "yesterday", "in 5 days", "3 days ago"])
		self.assertTrue(uses_deadline_variables("Due {{ deadline_date }}"))
		self.assertTrue(uses_deadline_variables("", "{{ doc.deadline_activity }}"))
		self.assertFalse(uses_deadline_variables("{{ student_name }}", "{{ project_label }}"))
		doc = frappe.get_doc({"doctype": "IRB Timeline", "timeline_name": " T ", "milestones": [
			{"activity": "A", "start_date": "2026-05-02", "end_date": "2026-05-01"}]})
		with self.assertRaises(frappe.ValidationError):
			doc.insert()
		doc = frappe.get_doc({"doctype": "IRB Timeline", "timeline_name": "T", "milestones": []})
		with self.assertRaises(frappe.ValidationError):
			doc.insert()
		frappe.db.rollback()

	def test_paste_parser_reads_the_school_timelines(self):
		from sirb.sirb_api.irb_timelines import parse_activities_text

		doc = (
			"Deadlines for School of Climate change and Sustainability\n"
			"Activity\tDates\n"
			"Announcement date\t29th June 2026\n"
			"Start reviewing IRB forms by mentor\t25th July to 5th August\n"
			"IRB starts reviewing\t5th August-10th August\n"
			"Revise and re-submit (within 5 days or receiving decision)\t10th-15th August\n"
			"IRB orientation\t16th September, 2026\t2-4 pm\n"
			"Field proposal\t3rd October, 2026 6:00 PM\n"
			"Bad\t31st February 2026\n"
			"Later\tsoon\n"
			"Year end\t20th December to 5th January 2027\n"
		)
		r = parse_activities_text(doc, 2026)
		self.assertEqual(r["title"], "School of Climate change and Sustainability")
		got = [(x["start_date"], x["end_date"], x["time_note"], x["problem"]) for x in r["rows"]]
		self.assertEqual(got, [
			("2026-06-29", None, None, None),
			("2026-07-25", "2026-08-05", None, None),
			("2026-08-05", "2026-08-10", None, None),
			("2026-08-10", "2026-08-15", None, None),  # "10th-15th August": month shared
			("2026-09-16", None, "2-4 pm", None),
			("2026-10-03", None, "6:00 PM", None),  # note kept from the date cell
			(None, None, None, "The date doesn't exist"),
			(None, None, "soon", "No date found"),  # text kept as the note, date left to fill in
			("2026-12-20", "2027-01-05", None, None),
		])
		# No tabs (pasted from a PDF): the line is cut at the first date.
		row = parse_activities_text("IRB orientation – 16/09/2026 2-4 pm", 2026)["rows"][0]
		self.assertEqual((row["activity"], row["start_date"], row["time_note"]), ("IRB orientation", "2026-09-16", "2-4 pm"))

	def test_paste_parser_joins_wrapped_lines(self):
		from sirb.sirb_api.irb_timelines import parse_activities_text

		# Copied without tabs: each wrapped line of a cell arrives on its own line.
		wrapped = (
			"Deadlines for School of Climate change and Sustainability\n"
			"Activity Dates\n"
			"Last date for submission of IRB forms by student to the\n"
			"IRB Committee 25th July 2026\n"
			"Start reviewing IRB forms by mentor 25th July to 5th\n"
			"August\n"
			"Revise and re-submit (to IRB by students) (within 5\n"
			"days or receiving decision) 10th-15th August\n"
		)
		r = parse_activities_text(wrapped, 2026)
		self.assertEqual(r["title"], "School of Climate change and Sustainability")  # not "Activity Dates"
		self.assertEqual(
			[(x["activity"], x["start_date"], x["end_date"], x["time_note"]) for x in r["rows"]],
			[
				("Last date for submission of IRB forms by student to the IRB Committee", "2026-07-25", None, None),
				("Start reviewing IRB forms by mentor", "2026-07-25", "2026-08-05", None),
				("Revise and re-submit (to IRB by students) (within 5 days or receiving decision)", "2026-08-10", "2026-08-15", None),
			],
		)
