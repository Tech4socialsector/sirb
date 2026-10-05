# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Give IRB Programme Manager its permissions on sites whose IRB Project /
Faculty permissions were edited in Role Permission Manager.

Such a site keeps them as Custom DocPerm, which replaces the DocType's own
permissions entirely, so the manager rows shipped in irb_project.json and
faculty.json never apply there and managers couldn't open or edit projects.
Sites without Custom DocPerm use the JSON rows and are left alone.
"""

import frappe

from sirb.sirb.doctype.irb_programme_access.irb_programme_access import (
	PROGRAMME_MANAGER_ROLE,
	ensure_programme_manager_role,
)

# Same as the rows in irb_project.json / faculty.json.
ROWS = {
	"IRB Project": [{"permlevel": level, "read": 1, "write": 1 if level in (0, 5) else 0} for level in range(9)],
	"Faculty": [{"permlevel": 0, "select": 1}],
}


def execute():
	ensure_programme_manager_role()
	for doctype, rows in ROWS.items():
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			continue
		for row in rows:
			if frappe.db.exists(
				"Custom DocPerm", {"parent": doctype, "role": PROGRAMME_MANAGER_ROLE, "permlevel": row["permlevel"]}
			):
				continue
			frappe.get_doc(
				{"doctype": "Custom DocPerm", "parent": doctype, "role": PROGRAMME_MANAGER_ROLE, **row}
			).insert(ignore_permissions=True)
		frappe.clear_cache(doctype=doctype)
