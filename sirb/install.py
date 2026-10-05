# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

from sirb.sirb.doctype.irb_programme_access.irb_programme_access import (
	ensure_programme_manager_role,
	ensure_programme_viewer_role,
)
from sirb.sirb_api.alert_templates import ensure_default_templates
from sirb.sirb_api.status_email_templates import ensure_status_email_templates


def after_install():
	# Patches are marked as done (not run) on a fresh install, so seed here too.
	ensure_default_templates()
	ensure_status_email_templates()
	ensure_programme_viewer_role()
	ensure_programme_manager_role()
