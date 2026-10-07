# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Rename IRB Project's question-18 mentor feedback field from `heq_s18_` to
`heq_s18_mf`, the name every other section's field uses. The form's
review-highlighting code looks fields up as <section>_mf, and the missing
name stopped it partway, leaving later sections unmarked."""

from frappe.model.utils.rename_field import rename_field


def execute():
	rename_field("IRB Project", "heq_s18_", "heq_s18_mf")
