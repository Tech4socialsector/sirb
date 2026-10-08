# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

from sirb.sirb_api.worklists import get_secondary_reviewer_projects, worklist_report_columns


def execute(filters=None):
	# One row per project (a group project lists all its students), with
	# the same rule as the workspace card that opens this report and the
	# Vue portal's worklist tab.
	return worklist_report_columns(), get_secondary_reviewer_projects("pending")
