# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe

from sirb.utils import get_logged_in_doc

from frappe.query_builder import DocType

def execute(filters=None):
	columns = [
		{
			"fieldname": "project_id",
			"label": "Project Record (Click to view)",
			"fieldtype": "Link",
			"options": "IRB Project"
		},
		{
			"fieldname": "project_title",
			"label": "Project Title",
			"fieldtype": "Data",
		},		
		{
			"fieldname": "project_status",
			"label": "Project Status",
			"fieldtype": "Data",
		},
	]
	doc = get_logged_in_doc("Student")
	print(doc.system_user)
	if doc:
		data = frappe.db.sql(
			f'''select p.title as project_title, p.name as project_id, p.status as project_status 
			from tabStudent as s join `tabStudent Project Mapping` 
			as sp join `tabIRB Project` as p on s.name = sp.student and 
			sp.irb_project = p.name where s.system_user="{doc.system_user}" and sp.status="active"''', as_dict=1
		)
		print("DATA", data)
	else:
		data = []


	return columns, data

