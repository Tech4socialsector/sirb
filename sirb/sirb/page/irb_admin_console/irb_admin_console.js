// Copyright (c) 2026, Ram and contributors
// For license information, please see license.txt

frappe.pages["irb-admin-console"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "IRB Admin Console",
		single_column: true,
	});

	new IRBAdminConsole(page);
};

const STATUS_LABELS = {
	student_action: "Awaiting Approval Completion by Student",
	mentor_approval: "Awaiting Faculty Mentor Approval",
	mentor_correction: "Awaiting Student Correction for Mentor Feedback",
	primary_reviewer: "Awaiting Primary Reviewer Comments to Secondary Reviewer",
	secondary_reviewer: "Awaiting Secondary Reviewer Comments to Primary Reviewer",
	reviewer_feedback: "Awaiting Reviewer Feedback to Student",
	reviewer_correction: "Awaiting Student Correction for Reviewer Feedback",
	provisional: "Provisionally Approved",
	final_approval: "Awaiting Final Approval",
	approved: "Approved",
};

const STATUS_SHORT_LABELS = {
	student_action: "Student Action",
	mentor_approval: "Mentor Approval",
	mentor_correction: "Mentor Correction",
	primary_reviewer: "Primary Reviewer",
	secondary_reviewer: "Secondary Reviewer",
	reviewer_feedback: "Reviewer Feedback",
	reviewer_correction: "Reviewer Correction",
	provisional: "Provisional",
	final_approval: "Final Approval",
	approved: "Approved",
};

// visual grouping for consistent status coloring across the dashboard
const STATUS_COLOR = {
	student_action: "warning",
	mentor_approval: "warning",
	mentor_correction: "orange",
	primary_reviewer: "warning",
	secondary_reviewer: "warning",
	reviewer_feedback: "warning",
	reviewer_correction: "orange",
	provisional: "success-light",
	final_approval: "warning",
	approved: "success",
};

const CARD_ICONS = {
	total: "users",
	student_action: "user",
	mentor_approval: "user-check",
	reviewer_action: "eye",
	final_approval: "flag",
	provisional: "check-circle",
	approved: "check",
};

class IRBAdminConsole {
	constructor(page) {
		this.page = page;
		this.wrapper = $(page.body);
		this.filters = {};
		this.filter_options = null;

		this.setup_layout();
		this.setup_programme_search();
		this.load_filter_options().then(() => {
			this.setup_filters();
			this.refresh();
		});
	}

	setup_layout() {
		this.wrapper.html(`
			<div class="awd">
				<div class="awd-filters"></div>
				<div class="awd-cards"></div>

				<div class="awd-section">
					<div class="awd-section-header">
						<div>
							<h4>Workflow by Programme</h4>
							<span class="awd-section-sub">Programme-wise breakdown across every workflow stage</span>
						</div>
						<div class="awd-programme-toolbar">
							<span class="awd-programme-count"></span>
							<input type="text" class="form-control form-control-sm awd-programme-search" placeholder="Search programme...">
							<button class="btn btn-default btn-sm awd-export-programme" title="Export the rows currently shown to CSV">
								Export CSV
							</button>
						</div>
					</div>
					<div class="awd-table-wrap"><div class="awd-programme-table"></div></div>
				</div>

				<div class="awd-row awd-row-top">
					<div class="awd-col awd-col-chart">
						<div class="awd-section">
							<div class="awd-section-header">
								<div>
									<h4>Workflow Distribution</h4>
									<span class="awd-section-sub">Students in each workflow stage</span>
								</div>
							</div>
							<div class="awd-chart"></div>
						</div>
					</div>
					<div class="awd-col awd-col-pending">
						<div class="awd-section">
							<div class="awd-section-header">
								<div>
									<h4>Pending Actions</h4>
									<span class="awd-section-sub">Where action is required right now</span>
								</div>
							</div>
							<div class="awd-pending"></div>
						</div>
					</div>
				</div>

				<div class="awd-section">
					<div class="awd-section-header">
						<div>
							<h4>Workload by Role</h4>
							<span class="awd-section-sub">Faculty mentors and reviewers with pending work</span>
						</div>
					</div>
					<div class="awd-workload"></div>
				</div>

				<div class="awd-section">
					<div class="awd-section-header">
						<div>
							<h4>Recent Activity</h4>
							<span class="awd-section-sub">Latest workflow status changes</span>
						</div>
					</div>
					<div class="awd-activity"></div>
				</div>
			</div>
		`);
		this.inject_styles();
	}

	// ---------------------------------------------------------------- filters

	async load_filter_options() {
		this.filter_options = await this.call("get_filter_options");
	}

	setup_filters() {
		const opts = this.filter_options;
		const $f = this.wrapper.find(".awd-filters");

		const status_options = [""].concat(opts.statuses);

		$f.html(`
			<div class="awd-filter-bar">
				<div class="awd-filter-field" data-field="irb_unit"><label>Programme / Course</label></div>
				<div class="awd-filter-field" data-field="academic_year"><label>Academic Year</label></div>
				<div class="awd-filter-field" data-field="irb_cycle"><label>Batch / Cycle</label></div>
				<div class="awd-filter-field" data-field="status">
					<label>Status</label>
					<select class="form-control form-control-sm"></select>
				</div>
				<div class="awd-filter-field" data-field="faculty_mentor"><label>Faculty Mentor</label></div>
				<div class="awd-filter-field" data-field="primary_reviewer"><label>Primary Reviewer</label></div>
				<div class="awd-filter-field" data-field="secondary_reviewer"><label>Secondary Reviewer</label></div>
				<div class="awd-filter-field" data-field="from_date">
					<label>From</label>
					<input type="date" class="form-control form-control-sm">
				</div>
				<div class="awd-filter-field" data-field="to_date">
					<label>To</label>
					<input type="date" class="form-control form-control-sm">
				</div>
				<div class="awd-filter-actions">
					<button class="btn btn-primary btn-sm awd-apply">Apply Filters</button>
					<button class="btn btn-default btn-sm awd-clear">Clear Filters</button>
				</div>
			</div>
		`);

		// Plain single-select fields keep a native <select>.
		const $status_sel = $f.find('[data-field="status"] select');
		status_options.forEach((v) => {
			const text = v === "" ? "All" : v;
			$status_sel.append(`<option value="${frappe.utils.escape_html(v)}">${frappe.utils.escape_html(text)}</option>`);
		});

		// Multiselect fields use Frappe's standard MultiSelectList control
		// (the same one query report filters use) so multiple values can be
		// picked per field; each is mounted into its .awd-filter-field div.
		this.multiselect_controls = {};
		const make_multiselect = (fieldname, label, options) => {
			const $parent = $f.find(`[data-field="${fieldname}"]`);
			// the control's dropdown template always renders `option.description`,
			// so every option needs the key even when there is nothing to show.
			const options_with_description = options.map((opt) => Object.assign({ description: "" }, opt));
			const control = frappe.ui.form.make_control({
				parent: $parent.get(0),
				df: {
					fieldtype: "MultiSelectList",
					fieldname: fieldname,
					label: label,
					placeholder: "All",
					get_data: () => options_with_description,
				},
				render_input: true,
				only_input: true,
			});
			control.refresh();
			this.multiselect_controls[fieldname] = control;
		};

		make_multiselect(
			"irb_unit",
			"Programme / Course",
			opts.programmes.map((p) => ({ value: p.name, label: p.ao_name || p.name }))
		);
		make_multiselect(
			"academic_year",
			"Academic Year",
			opts.academic_years.map((y) => ({ value: y, label: y }))
		);
		make_multiselect(
			"irb_cycle",
			"Batch / Cycle",
			opts.cycles.map((c) => ({ value: c, label: c }))
		);
		make_multiselect(
			"faculty_mentor",
			"Faculty Mentor",
			opts.mentors.map((m) => ({ value: m.name, label: m.full_name || m.name }))
		);
		make_multiselect(
			"primary_reviewer",
			"Primary Reviewer",
			opts.reviewers.map((r) => ({ value: r.name, label: r.full_name || r.name }))
		);
		make_multiselect(
			"secondary_reviewer",
			"Secondary Reviewer",
			opts.reviewers.map((r) => ({ value: r.name, label: r.full_name || r.name }))
		);

		$f.find(".awd-apply").on("click", () => {
			const filters = {};

			Object.keys(this.multiselect_controls).forEach((fieldname) => {
				const values = this.multiselect_controls[fieldname].get_value();
				if (values && values.length) filters[fieldname] = values;
			});

			$f.find('[data-field="status"] select, [data-field="from_date"] input, [data-field="to_date"] input').each(
				function () {
					const field = $(this).closest("[data-field]").data("field");
					const val = $(this).val();
					if (val) filters[field] = val;
				}
			);

			this.filters = filters;
			this.refresh();
		});

		$f.find(".awd-clear").on("click", () => {
			Object.values(this.multiselect_controls).forEach((control) => control.set_value([]));
			$f.find('[data-field="status"] select').val("");
			$f.find('[data-field="from_date"] input, [data-field="to_date"] input').val("");
			this.filters = {};
			this.refresh();
		});
	}

	// ---------------------------------------------------------------- data

	call(method, args) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: `sirb.sirb.page.irb_admin_console.irb_admin_console.${method}`,
				args: args || {},
				callback: (r) => resolve(r.message),
				error: (r) => reject(r),
			});
		});
	}

	async refresh() {
		this.page.set_indicator("Loading...", "orange");
		const [data, activity, workload] = await Promise.all([
			this.call("get_dashboard_data", { filters: this.filters }),
			this.call("get_recent_activity", { filters: this.filters, limit: 25 }),
			this.call("get_role_workload", { filters: this.filters }),
		]);
		this.data = data;
		this.render_cards(data);
		this.render_programme_table(data);
		this.render_chart(data);
		this.render_pending_actions(data);
		this.render_workload(workload);
		this.render_activity(activity);
		this.page.set_indicator("Live", "green");
	}

	// ---------------------------------------------------------------- cards

	render_cards(data) {
		const sc = data.status_counts;
		const pa = data.pending_actions;

		const cards = [
			{
				label: "Total Students",
				value: data.total_students,
				drill: {},
				kind: "total",
				icon: CARD_ICONS.total,
			},
			{
				label: "Awaiting Student Action",
				value: pa.student_action_required,
				drill: { pending_group: "student_action_required" },
				kind: "warning",
				icon: CARD_ICONS.student_action,
			},
			{
				label: "Awaiting Faculty Mentor",
				value: pa.mentor_action_required,
				drill: { pending_group: "mentor_action_required" },
				kind: "warning",
				icon: CARD_ICONS.mentor_approval,
			},
			{
				label: "Awaiting Reviewer",
				value: pa.reviewer_action_required,
				drill: { pending_group: "reviewer_action_required" },
				kind: "warning",
				icon: CARD_ICONS.reviewer_action,
			},
			{
				label: "Awaiting Final Approval",
				value: pa.final_approval_required,
				drill: { pending_group: "final_approval_required" },
				kind: "warning",
				icon: CARD_ICONS.final_approval,
			},
			{
				label: "Provisionally Approved",
				value: sc.provisional,
				drill: { status_key: "provisional" },
				kind: "success-light",
				icon: CARD_ICONS.provisional,
			},
			{
				label: "Approved",
				value: sc.approved,
				drill: { status_key: "approved" },
				kind: "success",
				icon: CARD_ICONS.approved,
			},
		];

		const $c = this.wrapper.find(".awd-cards");
		$c.html(
			cards
				.map(
					(c) => `
			<div class="awd-card awd-clickable awd-card-${c.kind}" data-drill='${JSON.stringify(c.drill)}'>
				<div class="awd-card-icon awd-card-icon-${c.kind}">${frappe.utils.icon(c.icon, "sm")}</div>
				<div class="awd-card-body">
					<div class="awd-card-value">${c.value ?? 0}</div>
					<div class="awd-card-label">${frappe.utils.escape_html(c.label)}</div>
				</div>
			</div>`
				)
				.join("")
		);

		$c.find(".awd-clickable").on("click", (e) => {
			const drill = JSON.parse($(e.currentTarget).attr("data-drill"));
			const title = $(e.currentTarget).find(".awd-card-label").text();
			this.open_drilldown(drill, drill && Object.keys(drill).length ? undefined : "All Students");
		});
	}

	// ---------------------------------------------------------------- programme table

	render_programme_table(data) {
		const keys = Object.keys(STATUS_LABELS);
		this.programme_export_keys = keys;
		const $wrap = this.wrapper.find(".awd-programme-table");

		let head = `
			<table class="awd-table">
				<thead>
					<tr>
						<th class="awd-sticky-col">Programme / Course</th>
						<th>Total</th>
						${keys
							.map(
								(k) =>
									`<th title="${frappe.utils.escape_html(STATUS_LABELS[k])}">${frappe.utils.escape_html(
										STATUS_SHORT_LABELS[k]
									)}</th>`
							)
							.join("")}
					</tr>
				</thead>
				<tbody>
		`;

		if (!data.programme_matrix.length) {
			head += `<tr class="awd-no-results"><td colspan="${keys.length + 2}" class="text-muted text-center">No students match the current filters.</td></tr>`;
		} else {
			head += `<tr class="awd-no-search-results" style="display:none;"><td colspan="${keys.length + 2}" class="text-muted text-center">No programmes match your search.</td></tr>`;
		}

		data.programme_matrix.forEach((row) => {
			const programme_name = row.programme || row.irb_unit || "";
			head += `<tr data-programme-search="${frappe.utils.escape_html(programme_name.toLowerCase())}">
				<td class="awd-sticky-col">${frappe.utils.escape_html(programme_name)}</td>
				<td class="awd-total-cell">
					<span class="awd-cell-link" data-drill='${JSON.stringify({ irb_unit: row.irb_unit })}'>${row.total}</span>
				</td>
				${keys
					.map((k) => {
						const val = row.statuses[k] || 0;
						const display = val === 0 ? "0" : val;
						const drill = { irb_unit: row.irb_unit, status_key: k };
						return `<td class="awd-status-cell awd-status-${STATUS_COLOR[k]}">
							<span class="awd-cell-link" data-drill='${JSON.stringify(drill)}'>${display}</span>
						</td>`;
					})
					.join("")}
			</tr>`;
		});

		head += "</tbody></table>";
		$wrap.html(head);

		$wrap.find(".awd-cell-link").on("click", (e) => {
			const drill = JSON.parse($(e.currentTarget).attr("data-drill"));
			this.open_drilldown(drill);
		});

		// re-applies any search term still in the box (it survives table
		// re-renders, since it lives in the static layout markup) and
		// recomputes the count label for the freshly rendered rows.
		this.filter_programme_rows();
	}

	// Search box and export button live in the static layout markup, so
	// they are wired once (guarded by a data flag) rather than re-bound on
	// every refresh, which would otherwise stack duplicate handlers.
	setup_programme_search() {
		const $search = this.wrapper.find(".awd-programme-search");
		if ($search.data("awd-bound")) return;
		$search.data("awd-bound", true);
		$search.on("input", () => this.filter_programme_rows());

		this.wrapper.find(".awd-export-programme").on("click", () => this.export_programme_table());
	}

	// Exports exactly the rows currently visible in the table (i.e. respects
	// an active search term), read straight from the rendered DOM so the
	// export can never drift from what the admin is looking at.
	export_programme_table() {
		const keys = this.programme_export_keys || Object.keys(STATUS_LABELS);
		const header = ["Programme / Course", "Total"].concat(keys.map((k) => STATUS_LABELS[k]));
		const csv_rows = [header];

		const $rows = this.wrapper.find(".awd-programme-table tbody tr[data-programme-search]:visible");
		if (!$rows.length) {
			frappe.show_alert({ message: __("Nothing to export for the current search."), indicator: "orange" });
			return;
		}

		$rows.each(function () {
			const $cells = $(this).find("td");
			const row = [];
			$cells.each(function () {
				row.push($(this).text().trim());
			});
			csv_rows.push(row);
		});

		frappe.tools.downloadify(csv_rows, null, safe_filename("Workflow by Programme"));
	}

	filter_programme_rows() {
		const $wrap = this.wrapper.find(".awd-programme-table");
		const term = (this.wrapper.find(".awd-programme-search").val() || "").trim().toLowerCase();
		const $rows = $wrap.find("tbody tr").not(".awd-no-results, .awd-no-search-results");
		let visible = 0;

		$rows.each(function () {
			const match = !term || ($(this).attr("data-programme-search") || "").includes(term);
			$(this).toggle(match);
			if (match) visible += 1;
		});

		$wrap.find(".awd-no-search-results").toggle($rows.length > 0 && visible === 0);
		this.update_programme_count(visible, $rows.length);
	}

	update_programme_count(visible, total) {
		const $count = this.wrapper.find(".awd-programme-count");
		if (!total) {
			$count.text("");
		} else if (visible === total) {
			$count.text(`${total} programme${total === 1 ? "" : "s"}`);
		} else {
			$count.text(`${visible} of ${total} programmes`);
		}
	}

	// ---------------------------------------------------------------- chart

	render_chart(data) {
		// frappe.Chart registers a ResizeObserver + window listeners on
		// construction; destroying the previous instance before wiping the
		// container avoids callbacks firing against detached DOM nodes on
		// every filter-triggered refresh.
		if (this.chart && typeof this.chart.destroy === "function") {
			this.chart.destroy();
		}
		this.chart = null;

		const $c = this.wrapper.find(".awd-chart");
		$c.empty();

		const keys = Object.keys(STATUS_LABELS);
		const values = keys.map((k) => data.status_counts[k] || 0);

		// Constructing frappe.Chart before the browser has committed layout
		// for this container leaves it measuring a 0-width element, which
		// produces a malformed initial SVG that its own ResizeObserver then
		// crashes on when the real size lands. Deferring one frame ensures
		// layout (and the min-height in .awd-chart) is in place first.
		requestAnimationFrame(() => {
			if (!$c.is(":visible")) return;
			this.chart = new frappe.Chart($c[0], {
				data: {
					labels: keys.map((k) => STATUS_SHORT_LABELS[k]),
					datasets: [{ values }],
				},
				type: "bar",
				height: 260,
				colors: ["#5e64ff"],
				isNavigable: true,
				animate: false,
			});

			// frappe-charts emits a custom "data-select" DOM event on the
			// chart's container when isNavigable is true; the selected
			// index is tracked on the chart's own state.
			$c.off("data-select").on("data-select", () => {
				const idx = this.chart.state && this.chart.state.currentIndex;
				const key = keys[idx];
				if (key !== undefined && idx !== undefined) this.open_drilldown({ status_key: key });
			});
		});
	}

	// ---------------------------------------------------------------- pending actions

	render_pending_actions(data) {
		const pa = data.pending_actions;
		const items = [
			{ label: "Student Action Required", value: pa.student_action_required, group: "student_action_required", icon: "user" },
			{ label: "Faculty Mentor Action Required", value: pa.mentor_action_required, group: "mentor_action_required", icon: "user-check" },
			{ label: "Reviewer Action Required", value: pa.reviewer_action_required, group: "reviewer_action_required", icon: "eye" },
			{ label: "Final Approval Required", value: pa.final_approval_required, group: "final_approval_required", icon: "flag" },
		];

		const $p = this.wrapper.find(".awd-pending");
		$p.html(
			items
				.map(
					(i) => `
				<div class="awd-pending-row awd-clickable" data-group="${i.group}">
					<span class="awd-pending-icon">${frappe.utils.icon(i.icon, "xs")}</span>
					<span class="awd-pending-label">${frappe.utils.escape_html(i.label)}</span>
					<span class="awd-pending-value ${i.value ? "" : "awd-pending-value-zero"}">${i.value}</span>
				</div>`
				)
				.join("")
		);

		$p.find(".awd-clickable").on("click", (e) => {
			const group = $(e.currentTarget).data("group");
			this.open_drilldown({ pending_group: group });
		});
	}

	// ---------------------------------------------------------------- role workload

	render_workload(workload) {
		const $w = this.wrapper.find(".awd-workload");

		const sections = [
			{ title: "Faculty Mentors", role: "mentor", rows: workload.mentors },
			{ title: "Primary Reviewers", role: "primary_reviewer", rows: workload.primary_reviewers },
			{ title: "Secondary Reviewers", role: "secondary_reviewer", rows: workload.secondary_reviewers },
		];

		const render_section = (section) => {
			if (!section.rows.length) {
				return `
					<div class="awd-workload-col">
						<div class="awd-workload-title">${section.title}</div>
						<div class="text-muted small awd-empty">Nobody has pending work here.</div>
					</div>`;
			}
			return `
				<div class="awd-workload-col">
					<div class="awd-workload-title">${section.title}</div>
					${section.rows
						.map(
							(r) => `
						<div class="awd-workload-row awd-clickable" data-role="${section.role}" data-faculty="${frappe.utils.escape_html(r.faculty_id)}">
							<span class="awd-workload-name">${frappe.utils.escape_html(r.faculty_name || r.faculty_id)}</span>
							<span class="awd-workload-count">${r.pending_count}</span>
						</div>`
						)
						.join("")}
				</div>`;
		};

		$w.html(`<div class="awd-workload-grid">${sections.map(render_section).join("")}</div>`);

		$w.find(".awd-clickable").on("click", (e) => {
			const role = $(e.currentTarget).data("role");
			const faculty = $(e.currentTarget).data("faculty");
			this.open_drilldown({ role_person: { role, faculty } });
		});
	}

	// ---------------------------------------------------------------- recent activity

	render_activity(activity) {
		const $a = this.wrapper.find(".awd-activity");
		if (!activity.length) {
			$a.html(`<div class="text-muted small awd-empty">No recent status changes found.</div>`);
			return;
		}

		let html = `<table class="awd-table awd-activity-table">
			<thead><tr>
				<th>Student(s)</th><th>Programme</th><th>Action</th><th>Performed By</th><th>Date</th>
			</tr></thead><tbody>`;

		activity.forEach((a) => {
			html += `<tr class="awd-activity-row" data-project="${frappe.utils.escape_html(a.project_id)}">
				<td>${frappe.utils.escape_html(a.student_names || "-")}</td>
				<td>${frappe.utils.escape_html(a.programme || "-")}</td>
				<td>${frappe.utils.escape_html(a.from_status)} &rarr; <b>${frappe.utils.escape_html(a.to_status)}</b></td>
				<td>${frappe.utils.escape_html(a.performed_by || "-")}</td>
				<td>${comment_when(a.date)}</td>
			</tr>`;
		});
		html += "</tbody></table>";
		$a.html(html);

		$a.find(".awd-activity-row").on("click", (e) => {
			const project = $(e.currentTarget).data("project");
			frappe.set_route("app", "irb-project", project);
		});
	}

	// ---------------------------------------------------------------- drilldown modal

	async open_drilldown(drill, forced_title) {
		const filters = Object.assign({}, this.filters, drill.irb_unit ? { irb_unit: drill.irb_unit } : {});
		const args = { filters };
		const title_parts = [];

		if (drill.irb_unit) {
			const p = this.data.programme_matrix.find((r) => r.irb_unit === drill.irb_unit);
			title_parts.push(p ? p.programme : drill.irb_unit);
		}

		if (drill.status_key) {
			args.status = this.data.status_key_map[drill.status_key];
			title_parts.push(STATUS_LABELS[drill.status_key]);
		} else if (drill.pending_group) {
			args.pending_group = drill.pending_group;
			title_parts.push(
				{
					student_action_required: "Student Action Required",
					mentor_action_required: "Faculty Mentor Action Required",
					reviewer_action_required: "Reviewer Action Required",
					final_approval_required: "Final Approval Required",
				}[drill.pending_group]
			);
		} else if (drill.role_person) {
			args.role_person = drill.role_person;
			const role_labels = {
				mentor: "Faculty Mentor",
				primary_reviewer: "Primary Reviewer",
				secondary_reviewer: "Secondary Reviewer",
			};
			title_parts.push(`${role_labels[drill.role_person.role]} Pending Workload`);
		} else if (!drill.irb_unit) {
			title_parts.push(forced_title || "Students");
		}

		const title = title_parts.join(" — ");
		const rows = await this.call("get_drilldown_students", args);
		this.show_drilldown_dialog(title, rows);
	}

	show_drilldown_dialog(title, rows) {
		const dialog = new frappe.ui.Dialog({
			title: `${title} (${rows.length})`,
			size: "extra-large",
			fields: [{ fieldname: "table_html", fieldtype: "HTML" }],
			secondary_action_label: __("Export CSV"),
			secondary_action: () => this.export_drilldown_rows(title, rows),
		});

		let html = `<div class="awd-modal-table-wrap"><table class="awd-table">
			<thead><tr>
				<th>Student Name</th><th>Student ID</th><th>Programme</th>
				<th>Current Status</th><th>Faculty Mentor</th><th>Primary Reviewer</th>
				<th>Secondary Reviewer</th><th>Last Updated</th>
			</tr></thead><tbody>`;

		if (!rows.length) {
			html += `<tr><td colspan="8" class="text-muted text-center">No matching students.</td></tr>`;
		}

		rows.forEach((r) => {
			html += `<tr class="awd-modal-row" data-project="${frappe.utils.escape_html(r.project_id)}">
				<td>${frappe.utils.escape_html(r.student_name || "-")}</td>
				<td>${frappe.utils.escape_html(r.student_id || "-")}</td>
				<td>${frappe.utils.escape_html(r.programme || "-")}</td>
				<td>${frappe.utils.escape_html(r.status || "-")}</td>
				<td>${frappe.utils.escape_html(r.faculty_mentor || "-")}</td>
				<td>${frappe.utils.escape_html(r.primary_reviewer || "-")}</td>
				<td>${frappe.utils.escape_html(r.secondary_reviewer || "-")}</td>
				<td>${frappe.datetime.comment_when(r.last_updated)}</td>
			</tr>`;
		});
		html += "</tbody></table></div>";

		dialog.fields_dict.table_html.$wrapper.html(html);
		dialog.$wrapper.find(".awd-modal-row").on("click", function () {
			const project = $(this).data("project");
			dialog.hide();
			frappe.set_route("app", "irb-project", project);
		});

		dialog.show();
	}

	export_drilldown_rows(title, rows) {
		if (!rows.length) {
			frappe.show_alert({ message: __("Nothing to export."), indicator: "orange" });
			return;
		}

		const header = [
			"Student Name",
			"Student ID",
			"Programme",
			"Current Status",
			"Faculty Mentor",
			"Primary Reviewer",
			"Secondary Reviewer",
			"Last Updated",
		];
		const csv_rows = [header];

		rows.forEach((r) => {
			csv_rows.push([
				r.student_name || "-",
				r.student_id || "-",
				r.programme || "-",
				r.status || "-",
				r.faculty_mentor || "-",
				r.primary_reviewer || "-",
				r.secondary_reviewer || "-",
				r.last_updated || "-",
			]);
		});

		frappe.tools.downloadify(csv_rows, null, safe_filename(title || "Students"));
	}

	// ---------------------------------------------------------------- styles

	inject_styles() {
		$("#awd-styles").remove();
		$(`<style id="awd-styles">
			.awd { padding: 4px 2px 32px; }

			.awd-filter-bar { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end;
				background: var(--card-bg, #fff); border: 1px solid var(--border-color, #d1d8dd);
				border-radius: 10px; padding: 14px 16px; margin-bottom: 20px;
				box-shadow: 0 1px 2px rgba(16, 24, 40, .04); }
			.awd-filter-field { display: flex; flex-direction: column; min-width: 170px; }
			.awd-filter-field label { font-size: 11px; text-transform: uppercase; letter-spacing: .04em;
				color: var(--text-muted, #8d99a6); margin-bottom: 4px; font-weight: 600; }
			.awd-filter-actions { display: flex; gap: 8px; margin-left: auto; }

			/* MultiSelectList control: match the plain <select> filters visually */
			.awd-filter-field .multiselect-list { width: 100%; }
			.awd-filter-field .multiselect-list .form-control { min-height: 30px; display: flex;
				align-items: center; }
			.awd-filter-field .multiselect-list .dropdown-menu { min-width: 220px; max-width: 320px; }
			.awd-filter-field .selectable-item .small:empty { display: none; }

			.awd-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
				gap: 14px; margin-bottom: 22px; }
			.awd-card { display: flex; align-items: center; gap: 12px; border-radius: 10px; padding: 16px;
				background: var(--card-bg, #fff); border: 1px solid var(--border-color, #d1d8dd);
				transition: box-shadow .15s ease, transform .15s ease; }
			.awd-card-icon { display: flex; align-items: center; justify-content: center;
				width: 38px; height: 38px; border-radius: 9px; flex-shrink: 0; }
			.awd-card-icon svg { width: 18px; height: 18px; }
			.awd-card-value { font-size: 24px; font-weight: 700; line-height: 1.1; }
			.awd-card-label { font-size: 12px; color: var(--text-muted, #8d99a6); margin-top: 3px; font-weight: 500; }
			.awd-clickable { cursor: pointer; }
			.awd-card.awd-clickable:hover { box-shadow: 0 4px 14px rgba(16, 24, 40, .09); transform: translateY(-1px); }

			.awd-card-total .awd-card-icon { background: rgba(94, 100, 255, .1); color: #5e64ff; }
			.awd-card-total .awd-card-value { color: var(--text-color, #1c2126); }
			.awd-card-warning .awd-card-icon { background: rgba(201, 122, 0, .1); color: #c97a00; }
			.awd-card-warning .awd-card-value { color: #c97a00; }
			.awd-card-success .awd-card-icon { background: rgba(43, 147, 72, .12); color: #2b9348; }
			.awd-card-success .awd-card-value { color: #2b9348; }
			.awd-card-success-light .awd-card-icon { background: rgba(76, 154, 42, .1); color: #4c9a2a; }
			.awd-card-success-light .awd-card-value { color: #4c9a2a; }

			.awd-section { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #d1d8dd);
				border-radius: 10px; padding: 16px 18px; margin-bottom: 20px;
				box-shadow: 0 1px 2px rgba(16, 24, 40, .04); }
			.awd-section-header { display: flex; align-items: flex-start; justify-content: space-between;
				gap: 10px; margin-bottom: 14px; }
			.awd-section-header h4 { margin: 0; font-size: 14.5px; font-weight: 650; }
			.awd-section-sub { font-size: 12px; color: var(--text-muted, #8d99a6); }

			.awd-programme-toolbar { display: flex; align-items: center; gap: 10px; flex-shrink: 0; flex-wrap: wrap; }
			.awd-programme-count { font-size: 12px; color: var(--text-muted, #8d99a6); white-space: nowrap; }
			.awd-programme-search { width: 200px; }
			.awd-export-programme { white-space: nowrap; }

			.awd-chart { min-height: 260px; width: 100%; }

			.awd-table-wrap { overflow-x: auto; max-height: 560px; overflow-y: auto; border-radius: 8px; }
			.awd-table { border-collapse: collapse; width: 100%; font-size: 12.5px; white-space: nowrap; }
			.awd-table th, .awd-table td { border: 1px solid var(--border-color, #e4e8eb); padding: 8px 12px; text-align: center; }
			.awd-table thead th { position: sticky; top: 0; background: var(--subtle-fg, #f4f5f6); z-index: 2;
				font-weight: 650; color: var(--text-muted, #6b7280); font-size: 11.5px; text-transform: uppercase; letter-spacing: .02em; }
			.awd-sticky-col { position: sticky; left: 0; background: var(--card-bg, #fff); z-index: 1;
				text-align: left; font-weight: 550; white-space: normal; min-width: 170px; }
			.awd-table thead th.awd-sticky-col { z-index: 3; }
			.awd-table tbody tr:hover td { background: var(--subtle-fg, #fafbfc); }

			.awd-cell-link { cursor: pointer; font-weight: 650; color: var(--text-color, #1c2126);
				display: inline-block; min-width: 18px; }
			.awd-cell-link:hover { text-decoration: underline; color: var(--primary, #5e64ff); }
			.awd-total-cell .awd-cell-link { color: var(--primary, #5e64ff); }

			.awd-status-warning { background: rgba(255, 184, 0, .07); }
			.awd-status-orange { background: rgba(255, 138, 0, .09); }
			.awd-status-success { background: rgba(40, 167, 69, .07); }
			.awd-status-success-light { background: rgba(40, 167, 69, .035); }

			.awd-row { display: grid; grid-template-columns: 1.4fr 1fr; gap: 18px; }
			@media (max-width: 900px) { .awd-row { grid-template-columns: 1fr; } }

			.awd-pending-row { display: flex; align-items: center; gap: 10px;
				padding: 10px 4px; border-bottom: 1px solid var(--border-color, #eef0f2); }
			.awd-pending-row:last-child { border-bottom: none; }
			.awd-pending-icon { display: flex; color: var(--text-muted, #8d99a6); }
			.awd-pending-icon svg { width: 14px; height: 14px; }
			.awd-pending-label { flex: 1; font-size: 13px; }
			.awd-pending-value { font-weight: 700; font-size: 15px; color: #c97a00; min-width: 24px; text-align: right; }
			.awd-pending-value-zero { color: var(--text-muted, #8d99a6); font-weight: 600; }
			.awd-pending-row.awd-clickable:hover { background: var(--subtle-fg, #f8f9fa); border-radius: 6px; }

			.awd-workload-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
			@media (max-width: 900px) { .awd-workload-grid { grid-template-columns: 1fr; } }
			.awd-workload-title { font-size: 12px; font-weight: 650; text-transform: uppercase;
				letter-spacing: .03em; color: var(--text-muted, #8d99a6); margin-bottom: 8px; }
			.awd-workload-row { display: flex; align-items: center; justify-content: space-between;
				padding: 8px 8px; border-radius: 6px; font-size: 13px; }
			.awd-workload-row.awd-clickable:hover { background: var(--subtle-fg, #f8f9fa); }
			.awd-workload-count { font-weight: 700; background: rgba(201, 122, 0, .12); color: #c97a00;
				border-radius: 999px; padding: 1px 9px; font-size: 12px; }

			.awd-activity-row { cursor: pointer; }
			.awd-activity-row:hover { background: var(--subtle-fg, #f8f9fa); }
			.awd-empty { padding: 8px 2px; }
			.awd-modal-table-wrap { max-height: 60vh; overflow: auto; }
		</style>`).appendTo("head");
	}
}

function comment_when(date) {
	try {
		return frappe.datetime.comment_when(date);
	} catch (e) {
		return date;
	}
}

// Strips characters that are invalid in filenames on Windows/macOS/Linux
// (drill-down titles can contain " — " and other punctuation) and caps
// length so the download always succeeds.
function safe_filename(title) {
	return (title || "Export")
		.replace(/[\\/:*?"<>|]/g, "-")
		.replace(/\s+/g, " ")
		.trim()
		.slice(0, 120);
}
