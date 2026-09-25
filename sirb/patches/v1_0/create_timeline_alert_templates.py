# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

from sirb.sirb_api.alert_templates import ensure_default_templates


def execute():
	# One-time seed for sites installed before Timeline Alerts existed. Only
	# creates missing templates; existing (possibly edited) ones are left alone.
	ensure_default_templates()
