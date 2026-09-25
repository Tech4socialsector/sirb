// Copyright (c) 2026, Ram and contributors
// For license information, please see license.txt

frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Timeline Alert E-mail Delivery"] = {
	method: "sirb.sirb_api.timeline_alerts.get_email_delivery_chart",
	filters: [
		{
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: ["Last 7 Days", "Last 30 Days", "Last 90 Days"].join("\n"),
			default: "Last 30 Days",
			reqd: 1,
		},
	],
};
