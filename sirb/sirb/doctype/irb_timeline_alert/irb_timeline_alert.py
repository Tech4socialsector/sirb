# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from sirb.sirb_api.timeline_alerts import validate_alert


class IRBTimelineAlert(Document):
	def validate(self):
		# Shared with the portal: normalises filters, checks the template
		# renders and (re)computes next_run_at when the schedule changes.
		validate_alert(self)
