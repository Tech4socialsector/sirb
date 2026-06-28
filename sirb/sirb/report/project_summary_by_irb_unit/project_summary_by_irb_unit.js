// Copyright (c) 2026, Ram and contributors
// For license information, please see license.txt
frappe.query_reports["Project Summary By IRB Unit"] = {
	"filters": [
        {
            "fieldname": "irb_unit",
            "label": __("Filter by School/Programme"),
            "fieldtype": "Link",
            "options": "IRB Unit",
            "default": "-- Select --"
        },
	],
	onload: function(report) {
		// Fallback: DOM-level click on the chart SVG slices
		$(report.page.main).on("click", ".frappe-chart path", function() {
			// The selected data is tracked on the chart object
			const chart = report.chart;
			if (chart && chart.state) {
				const index = chart.curActiveSliceIndex;
				const label = chart.data.labels[index];
				frappe.set_route("query-report", "Projects by IRB Unit", {
					"status": label,
					"irb_unit": frappe.query_report.get_filter_value("irb_unit") || ""
				});
			}
		});
	}
}