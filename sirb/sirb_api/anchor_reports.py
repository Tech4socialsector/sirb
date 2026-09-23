# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Whitelisted wrappers around the Anchor-facing analytics reports
(Projects by IRB Unit, Project Summary by IRB Unit). Same query logic as
the original Script Reports, parametrized, restricted to the roles that
could already see these reports (Anchor, System Manager, Administrator).
"""

import json

import frappe

ALLOWED_ROLES = {"Anchor", "System Manager", "Administrator"}


def _check_permission():
	if not (set(frappe.get_roles()) & ALLOWED_ROLES):
		frappe.throw("You do not have permission to view this report.", frappe.PermissionError)


def _days_since_field_set_to_current_value(doctype: str, docname: str, fieldname: str):
	"""Ported verbatim from projects_by_irb_unit.py."""
	current_value = frappe.db.get_value(doctype, docname, fieldname)

	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": doctype, "docname": docname},
		fields=["data", "creation"],
		order_by="creation desc",
		limit_page_length=None,
	)

	for version in versions:
		changes = json.loads(version.data)
		for change in changes.get("changed", []):
			if change[0] == fieldname and change[2] == current_value:
				return frappe.utils.date_diff(frappe.utils.now_datetime(), version.creation)

	creation_time = frappe.db.get_value(doctype, docname, "creation")
	return frappe.utils.date_diff(frappe.utils.now_datetime(), creation_time)


@frappe.whitelist()
def get_projects_by_irb_unit(irb_unit=None, status=None, campus=None):
	"""Row-level detail: one row per active-or-approved project, with
	student names, mentor/reviewer names+emails, and days-in-current-status.

	Approved projects have their Student Project Mapping flipped to
	"inactive" (see IRBProject.on_change), so a plain `status = 'active'`
	filter here would silently drop every approved project from a
	*reports* page whose whole point is historical/complete analysis —
	matches the same `(sp.status = 'active' or p.status = 'Approved')`
	condition already used by the admin dashboard's BASE_JOIN.
	"""
	_check_permission()

	sp_data_list = frappe.db.sql(
		"""select GROUP_CONCAT(sp.student order by sp.student separator ',') as student_ids,
		sp.irb_project as project_id
		from `tabStudent Project Mapping` as sp
		join `tabIRB Project` as p on sp.irb_project = p.name
		where (sp.status = 'active' or p.status = 'Approved')
		group by sp.irb_project""",
		as_dict=True,
	)

	data = []
	for sp_data in sp_data_list:
		student_ids = sp_data["student_ids"].split(",")
		student_data = frappe.db.sql(
			"""select s.name, s.full_name, u.email from tabStudent as s
			join tabUser as u on s.system_user = u.name
			where s.name in %(student_ids)s""",
			{"student_ids": student_ids},
			as_dict=True,
		)
		student_info = [f"{s['full_name']} ({s['email']})" for s in student_data]

		params = {"project_id": sp_data["project_id"]}
		query = """select p.status, p.title, p.irb_cycle, p.modified, COALESCE(f1.full_name, '') as mentor_name,
			COALESCE(f1.system_user, '') as mentor_email, COALESCE(f2.full_name, '') as pr_name,
			COALESCE(f2.system_user, '') as pr_email, COALESCE(f3.full_name, '') as sr_name,
			COALESCE(f3.system_user, '') as sr_email, p.name, p.irb_unit
			from `tabIRB Project` as p
			left join tabFaculty as f1 on p.faculty_mentor = f1.name
			left join tabFaculty as f2 on p.primary_reviewer = f2.name
			left join tabFaculty as f3 on p.secondary_reviewer = f3.name
			where p.name = %(project_id)s"""
		if irb_unit:
			query += " and p.irb_unit = %(irb_unit)s"
			params["irb_unit"] = irb_unit
		if status:
			query += " and p.status = %(status)s"
			params["status"] = status
		if campus:
			campus_bounds = frappe.db.get_value("Academic Organizational Unit", campus, ["lft", "rgt"])
			if campus_bounds:
				lft, rgt = campus_bounds
				query += """ and p.irb_unit in (
					select iu.name from `tabIRB Unit` as iu
					join `tabAcademic Organizational Unit` as a on iu.ao_unit = a.name
					where a.lft >= %(lft)s and a.rgt <= %(rgt)s
				)"""
				params["lft"] = lft
				params["rgt"] = rgt

		project_data = frappe.db.sql(query, params, as_dict=True)
		if not project_data:
			continue
		p = project_data[0]

		irb_unit_name = ""
		if p["irb_unit"]:
			ao_data = frappe.db.sql(
				"""select a.ao_name from `tabIRB Unit` as u
				join `tabAcademic Organizational Unit` as a on u.ao_unit = a.name
				where u.name = %(irb_unit)s""",
				{"irb_unit": p["irb_unit"]},
				as_dict=True,
			)
			if ao_data:
				irb_unit_name = ao_data[0]["ao_name"]

		data.append(
			{
				"irb_unit": irb_unit_name,
				"project_status": p["status"],
				"project_title": p["title"],
				"irb_cycle": p["irb_cycle"],
				"last_updated": p["modified"],
				"days_in_state": _days_since_field_set_to_current_value("IRB Project", p["name"], "status"),
				"student_info": student_info,
				# Structured alongside the combined display strings above
				# (kept as-is for anything already reading them) so the
				# frontend can render "Name" with the email as secondary
				# text/tooltip instead of one long "Name (email)" string.
				"students": [{"name": s["full_name"], "email": s["email"]} for s in student_data],
				"mentor": f"{p['mentor_name']} ({p['mentor_email']})" if p["mentor_email"] else None,
				"mentor_name": p["mentor_name"] or None,
				"mentor_email": p["mentor_email"] or None,
				"primary_reviewer": f"{p['pr_name']} ({p['pr_email']})" if p["pr_email"] else None,
				"primary_reviewer_name": p["pr_name"] or None,
				"primary_reviewer_email": p["pr_email"] or None,
				"secondary_reviewer": f"{p['sr_name']} ({p['sr_email']})" if p["sr_email"] else None,
				"secondary_reviewer_name": p["sr_name"] or None,
				"secondary_reviewer_email": p["sr_email"] or None,
				"project_name": p["name"],
			}
		)

	return data


@frappe.whitelist()
def get_project_summary_by_irb_unit(irb_unit=None):
	"""Grouped project count by Programme x Status, with chart-ready data.

	Same active-or-approved condition as get_projects_by_irb_unit — see
	its docstring for why a plain `sp.status = 'active'` filter would
	drop every approved project from this summary.
	"""
	_check_permission()

	params = {}
	query = """select iu.ao_name as irb_unit, count(*) as project_count, p.status as project_status
		from `tabStudent Project Mapping` as sp
		join `tabIRB Project` as p on sp.irb_project = p.name
		join `tabIRB Unit` as iu on p.irb_unit = iu.name
		where (sp.status = 'active' or p.status = 'Approved')"""
	if irb_unit:
		query += " and p.irb_unit = %(irb_unit)s"
		params["irb_unit"] = irb_unit
	query += " group by p.status, iu.ao_name"

	results = frappe.db.sql(query, params, as_dict=True)

	return {
		"rows": results,
		"chart": {
			"type": "pie",
			"data": {
				"labels": [r["project_status"] for r in results],
				"datasets": [{"values": [r["project_count"] for r in results]}],
			},
		},
	}
