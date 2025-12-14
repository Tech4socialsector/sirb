# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe

from sirb.utils import get_logged_in_doc
from frappe.query_builder import DocType

def execute(filters=None):
	columns = [
		{
			"fieldname": "role",
			"label": "Role",
			"fieldtype": "Data",
		},
		{
			"fieldname": "count",
			"label": "Number",
			"fieldtype": "Int",
		},
	]
	doc = get_logged_in_doc("Faculty Mentor")
	data = []
	if doc:
		r = frappe.db.sql(
			'''select "Faculty Mentor", count(*) as count from tabStudent as s join `tabStudent Project` 
			as sp join tabProject as p on s.name = sp.parent and sp.project = p.name  where p.status='Awaiting Faculty mentor approval'
			and sp.full_name = {doc["full_name"]}
			''', as_dict=1
		)
		print(r)
		if r:
			data.extend(r)
		r = frappe.db.sql(
			'''select "Primary Reviewer", count(*) as count from tabStudent as s join `tabStudent Project` 
			as sp join tabProject as p on s.name = sp.parent and sp.project = p.name  where p.status='Awaiting reviewer feedback'
			and p.primary_reviewer = {doc["full_name"]}
			''', as_dict=1
		)	
		print(r)
		if r:
			data.extend(r)
		r = frappe.db.sql(
			'''select "Secondary Reviewer", count(*) as count from tabStudent as s join `tabStudent Project` 
			as sp join tabProject as p on s.name = sp.parent and sp.project = p.name  where p.status='Awaiting reviewer feedback'
			and p.secondary_reviewer = {doc["full_name"]}
			''', as_dict=1
		)	
		print(r)
		if r:
			data.extend(r)
	else:
		data = []


	return columns, data
