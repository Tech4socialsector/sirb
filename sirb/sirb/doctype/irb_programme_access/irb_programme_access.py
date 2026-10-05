# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Programme-scoped Admin Console access.

A user's IRB Programme Access record lists the programmes (IRB Units) they
may see, and its access level decides their role:

- Read only -> IRB Programme Viewer: the Admin Console for these programmes
  and nothing else. The role has no DocType permissions and no Desk access.
- Read & Write -> IRB Programme Manager: the same console, plus opening
  these programmes' projects to reassign the mentor/reviewers and set the
  status, like an administrator (sirb.permissions.manages_project). Every
  other field stays locked.

Every Admin Console query is narrowed to these units
(irb_admin_console.allowed_irb_units). No record, or no rows, means no data.

This is a dedicated record rather than Frappe User Permissions on IRB Unit,
because those would also narrow IRB Project access for a viewer who is
also a mentor or reviewer.
"""

import frappe
from frappe.model.document import Document

PROGRAMME_VIEWER_ROLE = "IRB Programme Viewer"
PROGRAMME_MANAGER_ROLE = "IRB Programme Manager"
READ_WRITE = "Read & Write"


def _ensure_role(role):
	# No Desk access: a user whose only role is this one becomes a Website
	# User and lands on the SIRB app (/sirb) instead of /app. Enforced even
	# when the role exists, because migrate auto-creates roles named in
	# DocType permissions (IRB Project, Faculty) with Desk access, before
	# this app's patches run.
	if not frappe.db.exists("Role", role):
		frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 0}).insert(ignore_permissions=True)
	elif frappe.db.get_value("Role", role, "desk_access"):
		frappe.db.set_value("Role", role, "desk_access", 0)


def ensure_programme_viewer_role():
	_ensure_role(PROGRAMME_VIEWER_ROLE)


def ensure_programme_manager_role():
	_ensure_role(PROGRAMME_MANAGER_ROLE)


def get_viewer_irb_units(user):
	"""IRB Units on `user`'s access record (empty if there is none)."""
	return frappe.get_all(
		"IRB Programme Access Unit",
		filters={"parenttype": "IRB Programme Access", "parentfield": "programmes", "parent": user},
		pluck="irb_unit",
		distinct=True,
	)


class IRBProgrammeAccess(Document):
	def validate(self):
		if self.user in ("Administrator", "Guest"):
			frappe.throw(f"{self.user} can't be given programme-scoped access.")
		if not self.programmes:
			frappe.throw("Add at least one programme.")
		seen = set()
		for row in self.programmes:
			if row.irb_unit in seen:
				frappe.throw(f"Row {row.idx}: {row.programme_name or row.irb_unit} is listed more than once.")
			seen.add(row.irb_unit)

	def on_update(self):
		# Exactly one of the two roles, matching the access level.
		ensure_programme_viewer_role()
		ensure_programme_manager_role()
		if self.access_level == READ_WRITE:
			wanted, other = PROGRAMME_MANAGER_ROLE, PROGRAMME_VIEWER_ROLE
		else:
			wanted, other = PROGRAMME_VIEWER_ROLE, PROGRAMME_MANAGER_ROLE
		user = frappe.get_doc("User", self.user)
		current = {r.role for r in user.roles}
		if wanted in current and other not in current:
			return
		if other in current:
			user.set("roles", [r for r in user.roles if r.role != other])
		if wanted not in current:
			user.append("roles", {"role": wanted})
		user.save()

	def on_trash(self):
		if frappe.db.exists("User", self.user):
			frappe.get_doc("User", self.user).remove_roles(PROGRAMME_VIEWER_ROLE, PROGRAMME_MANAGER_ROLE)
