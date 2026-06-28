# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns = [
		{
			"fieldname": "irb_unit",
			"label": "School/Programme",
			"fieldtype": "Data",
		},		
		{
			"fieldname": "project_status",
			"label": "Project Status",
			"fieldtype": "Data",
		},
		{
			"fieldname": "project_count",
			"label": "Project count",
			"fieldtype": "Int",
		},				
	]
	query = f'''select iu.ao_name as irb_unit, count(*) as project_count, p.status as project_status
		from `tabStudent Project Mapping` as sp join `tabIRB Project` as p join `tabIRB Unit` as iu 
		where sp.irb_project = p.name and p.irb_unit = iu.name'''
	if filters and filters["irb_unit"]:
		query += f' and p.irb_unit = \"{filters["irb_unit"]}\" '
	query += ' and sp.status = "Active" group by project_status'
	#print(query)
	results = frappe.db.sql(query, as_dict=1)
	#print(results)
	data = []
	for r in results:
		data.append({"irb_unit": r["irb_unit"], "project_count": r["project_count"], "project_status": r["project_status"]})
	print(data)
	chart = {
		"type": "pie",
		"data": {
			"labels": [x["project_status"] for x in data],
			"datasets": [{"values": [x["project_count"] for x in data]}]
		},
		"isNavigable": True
	}
	return columns, results, "Project count by status for School/Programme", chart
