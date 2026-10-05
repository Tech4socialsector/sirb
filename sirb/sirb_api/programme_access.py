# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Whitelisted CRUD for the portal's Programme Access page: which users get
the programme-scoped Admin Console (IRB Programme Access), read only or
read & write.

System Manager only. Writes go through the DocType, so its controller still
validates the programmes and keeps the user's Viewer / Manager role in step
with the access level.
"""

import frappe

from sirb.sirb.doctype.irb_programme_access.irb_programme_access import (
	PROGRAMME_MANAGER_ROLE,
	PROGRAMME_VIEWER_ROLE,
	READ_WRITE,
)

ACCESS = "IRB Programme Access"
ACCESS_LEVELS = ("Read only", READ_WRITE)


def _require_admin():
	frappe.only_for("System Manager")


@frappe.whitelist()
def get_programme_access():
	"""Every access record with its programmes, plus the programmes to pick from."""
	_require_admin()

	records = frappe.db.sql(
		f"""
		select a.name as user, u.full_name, u.enabled,
			ifnull(nullif(a.access_level, ''), 'Read only') as access_level,
			exists(select 1 from `tabHas Role` as hr
				where hr.parent = a.user and hr.parenttype = 'User'
				and hr.role = if(a.access_level = %(read_write)s, %(manager)s, %(viewer)s)) as has_role,
			a.modified
		from `tab{ACCESS}` as a
		left join tabUser as u on u.name = a.user
		order by u.full_name asc, a.name asc
		""",
		{"read_write": READ_WRITE, "manager": PROGRAMME_MANAGER_ROLE, "viewer": PROGRAMME_VIEWER_ROLE},
		as_dict=True,
	)

	rows = frappe.get_all(
		"IRB Programme Access Unit",
		filters={"parenttype": ACCESS, "parentfield": "programmes"},
		fields=["parent", "irb_unit"],
		order_by="idx asc",
	)
	names = {u.name: u.ao_name for u in frappe.get_all("IRB Unit", fields=["name", "ao_name"])}
	by_user = {}
	for r in rows:
		by_user.setdefault(r.parent, []).append({"irb_unit": r.irb_unit, "programme_name": names.get(r.irb_unit) or r.irb_unit})
	for rec in records:
		rec.programmes = by_user.get(rec.user, [])

	programmes = frappe.db.sql(
		"""select iu.name, iu.ao_name, count(p.name) as project_count
		from `tabIRB Unit` as iu
		left join `tabIRB Project` as p on p.irb_unit = iu.name
		group by iu.name
		order by iu.ao_name asc""",
		as_dict=True,
	)

	return {"records": records, "programmes": programmes}


@frappe.whitelist()
def save_programme_access(user, programmes, is_new=0, access_level="Read only"):
	"""Create (is_new) or replace a user's programme list and access level.
	Returns the user."""
	_require_admin()
	if isinstance(programmes, str):
		programmes = frappe.parse_json(programmes)
	programmes = [p for p in (programmes or []) if p]
	user = (user or "").strip()

	if not user or not frappe.db.exists("User", user):
		frappe.throw("Select a valid user.")
	if not programmes:
		frappe.throw("Select at least one programme.")
	if access_level not in ACCESS_LEVELS:
		frappe.throw("Select a valid access level.")
	missing = [p for p in programmes if not frappe.db.exists("IRB Unit", p)]
	if missing:
		frappe.throw("Some selected programmes no longer exist. Reload the page and try again.")
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		frappe.throw(f"{user} is an administrator and already sees every programme.")

	exists = frappe.db.exists(ACCESS, user)
	if frappe.utils.cint(is_new) and exists:
		frappe.throw(f"{user} already has programme access. Edit their existing entry instead.")
	if not frappe.utils.cint(is_new) and not exists:
		frappe.throw(f"{user} no longer has programme access. Reload the page and try again.")

	doc = frappe.get_doc(ACCESS, user) if exists else frappe.new_doc(ACCESS)
	if not exists:
		doc.user = user
	doc.access_level = access_level
	doc.set("programmes", [{"irb_unit": p} for p in dict.fromkeys(programmes)])
	doc.save() if exists else doc.insert()
	return doc.name


@frappe.whitelist()
def delete_programme_access(user):
	"""Remove the record; its controller also removes the viewer / manager role."""
	_require_admin()
	if not frappe.db.exists(ACCESS, user):
		frappe.throw(f"{user} no longer has programme access. Reload the page and try again.")
	frappe.delete_doc(ACCESS, user)
