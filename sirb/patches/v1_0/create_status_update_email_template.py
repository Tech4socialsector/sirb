# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

from sirb.sirb_api.status_email_templates import ensure_status_email_templates


def execute():
	# "Status Update Email Template" (the mentor's no-action e-mail on an
	# approval) shipped after create_status_email_templates had already run.
	# Only creates missing templates; existing ones are left alone.
	ensure_status_email_templates()
