# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe

from frappe.query_builder import DocType

from sirb.utils import get_logged_in_doc

def execute(filters=None):
	columns = [
		{
			"fieldname": "student_id",
			"label": "Student Record (Click to view)",
			"fieldtype": "Link",
			"options": "Student"
		},
		{
			"fieldname": "student_name",
			"label": "Student name",
			"fieldtype": "Data",
		},		
		{
			"fieldname": "project_title",
			"label": "Project Title",
			"fieldtype": "Data",
		},
		{
			"fieldname": "project_name",
			"label": "Project Record (Click to view)",
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname": "project_status",
			"label": "Project Status",
			"fieldtype": "Data",
		},
	]
	doc = get_logged_in_doc("Secondary Reviewer")
	if doc:
		data = frappe.db.sql(
			f'''select s.name as student_id, s.display_full_name as student_name, p.title as project_title, p.name as project_name, p.status as project_status from tabStudent as s join `tabStudent Project` 
			as sp join tabProject as p join tabFaculty as f on s.name = sp.parent and 
			sp.project = p.name  and p.secondary_reviewer=f.name and f.full_name="{doc.full_name}" and
			p.status = "Awaiting reviewer feedback"''', as_dict=1
		)
	else:
		data = []


	return columns, data

