# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

import json

import frappe

from sirb.sirb.doctype.irb_project.irb_project import reactivate_student_mappings


def execute():
	# Approval marks a project's Student Project Mappings inactive, and moving
	# it back from Approved didn't undo that, so those projects dropped out of
	# every worklist (IRBProject.on_change now reactivates them). Repair the
	# ones already moved back: not Approved now, and their history shows a
	# status change away from Approved. Projects inactive for any other
	# reason are left alone.
	reverted = set()
	for v in frappe.get_all(
		"Version",
		filters={"ref_doctype": "IRB Project", "data": ["like", '%"Approved"%']},
		fields=["docname", "data"],
	):
		try:
			changed = json.loads(v.data).get("changed") or []
		except (TypeError, ValueError):
			continue
		if any(c[0] == "status" and c[1] == "Approved" and c[2] != "Approved" for c in changed if len(c) == 3):
			reverted.add(v.docname)

	for name in sorted(reverted):
		if frappe.db.get_value("IRB Project", name, "status") not in (None, "Approved"):
			reactivate_student_mappings(name)
