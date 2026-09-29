# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Exposes IRB Project's DocType metadata (fields, sections, tabs,
permlevels, depends_on/mandatory_depends_on expressions) so the Vue
questionnaire renderer can build the form generically instead of
hand-duplicating ~300 field definitions. The permlevel numbers returned
here are descriptive only — Frappe's own server-side permission engine is
still what actually enforces field-level read/write access on save.
"""

import frappe

RENDERABLE_FIELDTYPES = {
	"Data",
	"Small Text",
	"Text",
	"Long Text",
	"Select",
	"Check",
	"Int",
	"Float",
	"Date",
	"Attach",
	"Link",
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
}


@frappe.whitelist()
def get_irb_project_schema():
	"""Ordered, filtered field metadata for IRB Project — enough for the
	frontend to reconstruct tabs/sections/fields and their conditional
	visibility, without leaking internal-only fieldtypes.
	"""
	meta = frappe.get_meta("IRB Project")
	fields = []
	for df in meta.fields:
		if df.fieldtype not in RENDERABLE_FIELDTYPES:
			continue
		fields.append(
			{
				"fieldname": df.fieldname,
				"fieldtype": df.fieldtype,
				"label": df.label,
				"options": df.options,
				"reqd": df.reqd,
				"read_only": df.read_only,
				"depends_on": df.depends_on,
				"mandatory_depends_on": df.mandatory_depends_on,
				"read_only_depends_on": df.read_only_depends_on,
				"description": df.description,
				"permlevel": df.permlevel,
				"default": df.default,
			}
		)
	return {"fields": fields, "field_order": meta.get("field_order") or [f.fieldname for f in meta.fields]}
