# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class IRBAlertRun(Document):
	"""One send of a Timeline Alert. Created and updated only by
	sirb.sirb_api.timeline_alerts."""
