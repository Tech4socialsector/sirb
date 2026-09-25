# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from sirb.sirb_api.irb_timelines import validate_timeline


class IRBTimeline(Document):
	def validate(self):
		# Shared with the portal: dates, statuses, and deadlines still used by alerts.
		validate_timeline(self)

	def on_trash(self):
		from sirb.sirb_api.irb_timelines import check_timeline_not_in_use

		check_timeline_not_in_use(self.name)
