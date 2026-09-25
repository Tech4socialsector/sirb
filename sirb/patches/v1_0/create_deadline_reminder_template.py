# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

from sirb.sirb_api.alert_templates import DEADLINE_TEMPLATE_NAME, ensure_default_templates


def execute():
	# Only the new template: sites that ran the first patch may have deleted
	# one of the original defaults on purpose.
	ensure_default_templates(names=[DEADLINE_TEMPLATE_NAME])
