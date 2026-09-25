// Copyright (c) 2026, Ram and contributors
// For license information, please see license.txt

// Helps System Managers edit Timeline Alert e-mails in Desk: lists the
// variables Timeline Alerts provide and previews the *unsaved* template for a
// real student, flagging unknown variables (which would reach students as
// literal "{{ ... }}" text, so sending refuses them).

frappe.ui.form.on("Email Template", {
	refresh(frm) {
		if (!frappe.user.has_role("System Manager")) return;

		const name = frm.is_new() ? null : frm.doc.name;
		frappe
			.xcall("sirb.sirb_api.timeline_alerts.get_template_editor_info", { name })
			.then((info) => {
				// The form may have moved to another record while this loaded.
				if (!info || frm.doc.doctype !== "Email Template" || (frm.is_new() ? null : frm.doc.name) !== name) return;
				const esc = frappe.utils.escape_html;
				const var_list = (variables) =>
					variables.map((v) => `<code title="${esc(v.description)}">{{ ${esc(v.name)} }}</code>`).join(" ");
				const used = info.used_by.length
					? `<b>${__("Used by Timeline Alerts")}:</b> ${info.used_by.map(esc).join(", ")}.<br>`
					: "";

				// A status-change e-mail not also picked by a Timeline Alert:
				// Timeline Alert variables would render blank here.
				if (info.status_email_variables && !info.used_by.length) {
					frm.set_intro(
						`${__("Sent automatically when an IRB Project changes status. Variables available")}: ${var_list(
							info.status_email_variables
						)}<br>` + __("Hover a variable for its meaning."),
						"blue"
					);
					return;
				}

				frm.add_custom_button(__("Preview as Timeline Alert"), () => sirb_preview_timeline_alert(frm));
				frm.set_intro(
					`${used}${__("Variables available in Timeline Alerts")}: ${var_list(info.variables)}<br>` +
						__("Hover a variable for its meaning. Use Preview as Timeline Alert to check the e-mail before saving."),
					"blue"
				);
			})
			.catch(() => {
				// Informational only; the form works without it.
			});
	},
});

function sirb_preview_timeline_alert(frm) {
	frappe
		.xcall("sirb.sirb_api.timeline_alerts.preview_template_draft", {
			subject: frm.doc.subject || "",
			response: frm.doc.response || "",
			use_html: frm.doc.use_html ? 1 : 0,
			response_html: frm.doc.response_html || "",
		})
		.then((preview) => {
			const esc = frappe.utils.escape_html;
			const who = preview.recipient
				? __("Preview for {0}", [esc(`${preview.recipient.student_name} <${preview.recipient.email}>`)])
				: __("Preview with sample data (no student has a project yet)");
			const warning = preview.unknown_variables.length
				? `<div class="alert alert-warning">${__("Unknown variables")}: ${preview.unknown_variables
						.map((v) => `<code>{{ ${esc(v)} }}</code>`)
						.join(" ")}<br>${__(
						"Students would see these as-is, so Timeline Alerts won't send this template until they are fixed."
				  )}</div>`
				: "";

			const d = new frappe.ui.Dialog({
				title: __("Timeline Alert preview"),
				size: "large",
				fields: [{ fieldtype: "HTML", fieldname: "preview" }],
			});
			const $wrap = d.fields_dict.preview.$wrapper;
			$wrap.html(
				`${warning}<p class="text-muted small">${who}</p>` +
					`<p><b>${__("Subject")}:</b> <span class="sirb-preview-subject"></span></p>`
			);
			// Plain text for the subject; a sandboxed iframe (no scripts, forms
			// or navigation) for the body.
			$wrap.find(".sirb-preview-subject").text(preview.subject);
			const frame = document.createElement("iframe");
			frame.setAttribute("sandbox", "");
			frame.setAttribute("title", __("E-mail preview"));
			frame.style.cssText = "width:100%;height:420px;border:1px solid var(--border-color);border-radius:8px;background:#fff";
			frame.srcdoc = preview.html;
			$wrap.append(frame);
			d.show();
		})
		.catch(() => {
			// frappe.xcall already showed the server's message (e.g. a Jinja
			// syntax error); swallow the rejection so it isn't an uncaught error.
		});
}
