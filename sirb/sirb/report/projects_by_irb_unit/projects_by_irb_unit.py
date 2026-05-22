# Copyright (c) 2025, Ram and contributors
# For license information, please see license.txt

import frappe

from sirb.utils import get_logged_in_doc
from frappe.query_builder import DocType
import frappe
import json
from frappe.utils import date_diff, now_datetime

def days_since_field_set_to_current_value(doctype: str, docname: str, fieldname: str) -> int | None:
    """
    Calculate the number of days since the given field in a document was last set
    to its current value.

    Returns:
        An integer number of days, or None if the current value has never changed
        (i.e., it is the original value from when the document was created).
    """
    # Get the current value of the field from the database
    current_value = frappe.db.get_value(doctype, docname, fieldname)

    # Fetch all Versions for the document, ordered from newest to oldest
    versions = frappe.get_all(
        "Version",
        filters={"ref_doctype": doctype, "docname": docname},
        fields=["data", "creation"],
        order_by="creation desc",
        limit_page_length=None,
    )

    # Go through each version until we find when the value became what it is now
    for version in versions:
        # Parse the 'data' column, which stores changes
        changes = json.loads(version.data)

        # Look for the target field in the 'changed' list
        for change in changes.get("changed", []):
            if change[0] == fieldname and change[2] == current_value:
                return date_diff(now_datetime(), version.creation)

    # If the value was never changed, it has been the same since creation
    creation_time = frappe.db.get_value(doctype, docname, "creation")
    return date_diff(now_datetime(), creation_time)

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
			"fieldname": "days_in_state",
			"label": "Number of days in current state",
			"fieldtype": "Int",
		},		
		{
			"fieldname": "student_info",
			"label": "Student name and email",
			"fieldtype": "Data",
		},
		{
			"fieldname": "mentor",
			"label": "Faculty Mentor",
			"fieldtype": "Data",
		},
		{
			"fieldname": "pr",
			"label": "Primary Reviewer",
			"fieldtype": "Data",
		},
		{
			"fieldname": "sr",
			"label": "Secondary Reviewer",
			"fieldtype": "Data",
		},		
		{
			"fieldname": "project_name",
			"label": "Project Record (Click to view)",
			"fieldtype": "Link",
			"options": "IRB Project"
		},
	]
	print("filters ", filters)
	data = []
	sp_data_list = frappe.db.sql('''select GROUP_CONCAT(student ORDER BY student SEPARATOR ', ') as student_ids, 
	irb_project as project_id from `tabStudent Project Mapping` where status='active' 
	group by irb_project''', as_dict=1)
	print(sp_data_list)
	if sp_data_list and len(sp_data_list) > 0:
		for sp_data in sp_data_list:
			data_item = {}
			print(sp_data)
			student_ids = sp_data["student_ids"].split(',')
			student_ids = [f"'{s}'" for s in student_ids]
			student_ids_str = ', '.join(student_ids)
			print(student_ids_str)
			q = f'''select s.name, s.full_name, u.email from tabStudent as s join 
			tabUser as u where s.system_user = u.name and s.name in ({student_ids_str})'''
			print(q)
			student_data = frappe.db.sql(q, as_dict = 1)
			print(student_data)
			student_info = []
			for s in student_data:
				student_info.append(f"{s['full_name']} ({s['email']})")
			data_item["student_info"] = "<br>".join(student_info)
			q2 = f'''select p.status, COALESCE(f1.full_name, '') as mentor_name, 
								COALESCE(f1.system_user, '') as mentor_email, COALESCE(f2.full_name, '') 
								as pr_name, COALESCE(f2.system_user, '') as pr_email, 
								COALESCE(f3.full_name, '') as sr_name, COALESCE(f3.system_user, '') as 
								sr_email, p.name, p.irb_unit from `tabIRB Project` as p 
								left join tabFaculty as f1 on p.faculty_mentor = f1.name left join 
								tabFaculty as f2 on p.primary_reviewer = f2.name left join 
								tabFaculty as f3 on p.secondary_reviewer = f3.name where 
								p.name = "{sp_data["project_id"]}"'''
			if filters:
				if "irb_unit" in filters:
					q2 += f' and p.irb_unit = "{filters["irb_unit"]}"'
				if "status" in filters:
					q2 += f' and p.status = "{filters["status"]}"'
			print(q2)
			project_data = frappe.db.sql(q2, as_dict = 1)
			print('Project data ', project_data)
			if project_data:
				data_item["project_status"] = project_data[0]["status"]
				if project_data[0]['mentor_email']:
					data_item["mentor"] = f"{project_data[0]["mentor_name"]} ({project_data[0]['mentor_email']})"
				else:
					data_item["mentor"] = 'None'
				data_item["pr"] = f"{project_data[0]['pr_name']} ({project_data[0]['pr_email']})"
				data_item["sr"] = f"{project_data[0]['sr_name']} ({project_data[0]['sr_email']})"
				data_item["project_name"] = project_data[0]["name"]
				data_item["days_in_state"] = days_since_field_set_to_current_value("IRB Project", project_data[0]["name"], "status")
				data_item["irb_unit"] = ''
				if project_data[0]["irb_unit"]:
					q3 = f'''select a.ao_name from `tabIRB Unit` as u join `tabAcademic Organizational Unit` 
					as a where u.ao_unit = a.name and u.name = "{project_data[0]["irb_unit"]}"'''
					ao_data = frappe.db.sql(q3, as_dict = 1)
					if ao_data:
						data_item["irb_unit"] = ao_data[0]["ao_name"]
				data.append(data_item)

			

	# data = frappe.db.sql(
	# 	f'''select s.name as student_id, s.full_name as student_name, 
	# 	p.title as project_title, p.name as project_name, p.status as project_status 
	# 	from tabStudent as s join `tabStudent Project Mapping` 
	# 	as sp join `tabIRB Project` as p join tabFaculty as f on s.name = sp.student and 
	# 	sp.irb_project = p.name  and p.faculty_mentor=f.name where f.system_user="{doc.system_user}" 
	# 	and p.status = "Approved"''', as_dict=1
	# )
	#print(data)
	# print(data)
	print('data ', data)
	return columns, data
