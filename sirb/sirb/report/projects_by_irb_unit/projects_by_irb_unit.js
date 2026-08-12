// Copyright (c) 2026, Ram and contributors
// For license information, please see license.txt

async function get_select_field_options(doctype, fieldname) {
    let options = [];
    await frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "DocType",
            filters: { name: doctype },
            fieldname: `fields`
        },
        callback: function(response) {
            const fields = response.message.fields;
            // Find the specific field
            const target_field = fields.find(f => f.fieldname === fieldname);
            if (target_field && target_field.fieldtype === "Select") {
                // Split the newline-separated options string into an array
                options = target_field.options.split("\n").filter(opt => opt.trim());
            }
        }
    });
	console.log(options)
    return options;
}

frappe.query_reports["Projects by IRB Unit"] = {
	"filters": [
        {
            "fieldname": "campus",
            "label": __("Filter by Campus"),
            "fieldtype": "Link",
            "options": "Academic Organizational Unit",
            "get_query": function() {
                return {
                    filters: { "ao_type": "Campus" }
                };
            }
        },
        {
            "fieldname": "irb_unit",
            "label": __("Filter by School/Programme"),
            "fieldtype": "Link",
            "options": "IRB Unit",
            "default": "-- Select --"
        },
		{
            "fieldname": "status",
            "label": __("Filter by project status"),
            "fieldtype": "Select", // Use Select fieldtype
		}
	],
    onload: function(report) {
        // Get the IRB Project Doctype's metadata
        let irb_project_meta = frappe.get_meta("IRB Project");
        // Find the 'status' field
        let status_field = irb_project_meta.fields.find(f => f.fieldname === "status");
        // Get its options (which is a newline-separated string)
        let options_string = status_field.options;
        // Split the string into an array of individual options
        let options_array = options_string.split("\n");
        // Add an empty value at the beginning to allow clearing the filter
        options_array.unshift("");
        // Convert the array back to a newline-separated string for the filter
        let options_string_with_empty = options_array.join("\n");

        let status_filter = report.filters.find(filter => filter.fieldname === "status");
        if (status_filter) {
            status_filter.df.options = options_string_with_empty;
            status_filter.refresh();
        }
    }
};

