# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

from sirb.sirb_api.status_email_templates import ensure_status_email_templates


def execute():
	# Sites set up before these templates shipped with the app (e.g. local
	# development sites). Only creates missing ones; the live site's
	# existing templates are left alone.
	ensure_status_email_templates()
