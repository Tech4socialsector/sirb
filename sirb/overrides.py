# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Frappe endpoints that return a whole IRB Project, minus what the
viewer may not see on it (sirb.permissions.hidden_project_fields): its
mentor may not see the reviewers or what they write, its students the
reviewers or their internal notes, its reviewers the mentor. Wired up through
override_whitelisted_methods in hooks.py.

Desk form loads: Frappe builds the form's timeline (docinfo) with permissions ignored: the
latest Versions with every changed field's old and new value, comments, and
who did each thing. Hidden fields' changes are dropped and people the
viewer may not know are shown by role (sirb.permissions.person_masker). (The doc itself is filtered by
IRBProject.apply_fieldlevel_read_permissions.)
"""

import json

import frappe
from frappe import client
from frappe.desk import listview, reportview
from frappe.desk.form import load
from frappe.utils import get_safe_filters

from sirb.permissions import (
	REVIEWER_LABEL,
	hidden_on_any_project,
	hidden_project_fields,
	hidden_project_fields_by_name,
	mask_project_rows,
	maskable_project_fields,
	person_masker,
)

# docinfo lists whose rows name a user, and the key that holds it.
_USER_KEYS = {
	"assignments": "owner",
	"assignment_logs": "owner",
	"attachment_logs": "owner",
	"info_logs": "owner",
	"like_logs": "owner",
	"workflow_logs": "owner",
	"views": "owner",
	"energy_point_logs": "owner",
	"shared": "user",
	"communications": "sender",
	"automated_messages": "sender",
}


@frappe.whitelist()
def getdoc(doctype, name):
	load.getdoc(doctype, name)
	_filter_docinfo(doctype, name)


@frappe.whitelist()
def get_docinfo(doc=None, doctype=None, name=None):
	load.get_docinfo(doc, doctype, name)
	if doc is not None:
		doctype, name = doc.doctype, doc.name
	_filter_docinfo(doctype, name)


@frappe.whitelist(methods=["POST", "PUT"])
def set_value(doctype, name, fieldname, value=None):
	"""frappe.client.set_value (the Vue page saves with it) answers with the
	whole saved doc, which skips apply_fieldlevel_read_permissions."""
	saved = client.set_value(doctype, name, fieldname, value)
	if doctype == "IRB Project":
		for hidden in hidden_project_fields(frappe.get_doc(doctype, name)):
			saved.pop(hidden, None)
	return saved


# List endpoints: Desk's list / report view, frappe.db.get_list and
# get_value. Frappe gives every row the columns the user's global roles may
# read, so e.g. a reviewer saw each project's faculty mentor in the IRB
# Project list. Each value is blanked where its project hides that field
# from the user (sirb.permissions.mask_project_rows).


def _is_project(doctype):
	return doctype == "IRB Project"


def _fieldname(field):
	"""`tabIRB Project`.`faculty_mentor` -> faculty_mentor."""
	return str(field).split(".")[-1].strip("` ")


@frappe.whitelist()
@frappe.read_only()
def reportview_get():
	data = reportview.get()
	if _is_project(frappe.form_dict.get("doctype")) and isinstance(data, dict) and data.get("values"):
		data["values"] = mask_project_rows(data["values"], data["keys"])
	return data


@frappe.whitelist()
@frappe.read_only()
def reportview_get_list():
	if not _is_project(frappe.form_dict.get("doctype")):
		return reportview.get_list()
	# Rows as dicts, so each value can be matched to its column; given back
	# in the shape asked for.
	pluck = frappe.form_dict.pop("pluck", None)
	as_list = frappe.utils.sbool(frappe.form_dict.pop("as_list", False))
	if pluck:
		frappe.form_dict.fields = json.dumps(["name", pluck])
	rows = mask_project_rows(reportview.get_list())
	if pluck:
		return [row.get(_fieldname(pluck)) for row in rows]
	return [list(row.values()) for row in rows] if as_list else rows


@frappe.whitelist()
def client_get_list(
	doctype,
	fields=None,
	filters=None,
	group_by=None,
	order_by=None,
	limit_start=None,
	limit_page_length=20,
	parent=None,
	debug: bool = False,
	as_dict: bool = True,
	or_filters=None,
	expand=None,
):
	args = dict(
		fields=fields,
		filters=filters,
		group_by=group_by,
		order_by=order_by,
		limit_start=limit_start,
		limit_page_length=limit_page_length,
		parent=parent,
		debug=debug,
		or_filters=or_filters,
		expand=expand,
	)
	if not _is_project(doctype):
		return client.get_list(doctype, as_dict=as_dict, **args)
	rows = mask_project_rows(client.get_list(doctype, as_dict=True, **args))
	return rows if as_dict else [list(row.values()) for row in rows]


@frappe.whitelist()
def client_get_value(doctype, fieldname, filters=None, as_dict=True, debug=False, parent=None):
	value = client.get_value(doctype, fieldname, filters, as_dict, debug, parent)
	if not _is_project(doctype) or value is None:
		return value
	try:
		fields = frappe.parse_json(fieldname)
	except (TypeError, ValueError):
		fields = [fieldname]
	if not isinstance(fields, list | tuple):
		fields = [fields]
	if not {_fieldname(f) for f in fields} & maskable_project_fields():
		return value

	# The project, when the filters name it; else every project they can open.
	filters = get_safe_filters(filters)
	if isinstance(filters, dict):
		filters = filters.get("name")
	if isinstance(filters, str | int) and str(filters):
		hidden = hidden_project_fields_by_name([filters]).get(str(filters), maskable_project_fields())
	else:
		hidden = hidden_on_any_project()

	# The shape client.get_value returned: a dict, one value per field, or
	# a lone value for a single field.
	if isinstance(value, dict):
		return {k: None if _fieldname(k) in hidden else v for k, v in value.items()}
	if isinstance(value, list | tuple) and len(fields) > 1:
		return [None if _fieldname(f) in hidden else v for f, v in zip(fields, value)]
	return None if _fieldname(fields[0]) in hidden else value


@frappe.whitelist()
def get_group_by_count(doctype: str, current_filters: str, field: str) -> list[dict]:
	"""The list sidebar's counts per value (e.g. per faculty mentor) would
	name people a user may not know about; none for such a field."""
	if _is_project(doctype) and field in hidden_on_any_project():
		return []
	return listview.get_group_by_count(doctype, current_filters, field)


@frappe.whitelist()
@frappe.read_only()
def export_query():
	"""Report view export writes the file itself, so leave out of it the
	columns hidden on any project the user can open."""
	if _is_project(frappe.form_dict.get("doctype")):
		hidden = hidden_on_any_project()
		fields = frappe.parse_json(frappe.form_dict.get("fields") or "[]")
		if hidden and isinstance(fields, list):
			frappe.form_dict.fields = json.dumps([f for f in fields if _fieldname(f) not in hidden])
	return reportview.export_query()


def _filter_docinfo(doctype, name):
	docinfo = frappe.response.get("docinfo")
	if doctype != "IRB Project" or not docinfo:
		return
	# As saved: membership must not follow anything the request changed.
	doc = frappe.get_doc(doctype, name)
	hidden = hidden_project_fields(doc)
	if not hidden:
		return
	mask = person_masker(doc)

	versions = []
	for version in docinfo.get("versions") or []:
		try:
			data = json.loads(version.data)
		except (TypeError, ValueError):
			continue
		data["changed"] = [c for c in data.get("changed") or [] if c and c[0] not in hidden]
		if not any(data.get(key) for key in ("changed", "added", "removed", "row_changed")):
			continue
		version.data = json.dumps(data)
		version.owner = mask(version.owner)
		versions.append(version)
	docinfo.versions = versions

	# A reviewer's comment on the form is something they wrote, hidden along
	# with their other comments; anyone else's is shown under their label.
	comments = []
	for comment in docinfo.get("comments") or []:
		comment.owner = mask(comment.owner)
		if comment.owner != REVIEWER_LABEL:
			comments.append(comment)
	docinfo.comments = comments

	for key, user_key in _USER_KEYS.items():
		for row in docinfo.get(key) or []:
			if row.get(user_key):
				row[user_key] = mask(row[user_key])

	user_info = docinfo.get("user_info") or {}
	for user in [u for u in user_info if mask(u) != u]:
		user_info.pop(user)
