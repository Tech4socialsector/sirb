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
from frappe.desk.form import load

from sirb.permissions import REVIEWER_LABEL, hidden_project_fields, person_masker

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
