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
			"options": "IRB Project"
		},
		{
			"fieldname": "project_status",
			"label": "Project Status",
			"fieldtype": "Data",
		},
	]
	doc = get_logged_in_doc("Secondary Reviewer")
	print("DOC IS ", doc)
	if doc:
		data = frappe.db.sql(
			f'''select s.name as student_id, s.full_name as student_name, p.title as project_title, 
			p.name as project_name, p.status as project_status from tabStudent as s 
			join `tabStudent Project Mapping` 
			as sp join `tabIRB Project` as p join tabFaculty as f on s.name = sp.student and 
			sp.irb_project = p.name  and p.secondary_reviewer=f.name where f.system_user="{doc.system_user}" 
			and sp.status="active" and
			p.status = "Awaiting secondary reviewer comments"''', as_dict=1
		)
		print("DATA!!! ", data)
	else:
		data = []


	return columns, data

