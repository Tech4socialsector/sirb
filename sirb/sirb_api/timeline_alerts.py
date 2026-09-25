# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Timeline Alerts: bulk e-mail to students picked by filters, sent now or
on a schedule.

Flow
----
- The portal's Timeline Alerts page previews the students a filter set
  matches and renders the chosen Email Template for one of them.
- "Send now" creates an IRB Alert Run (status Queued) and enqueues
  `execute_run` after the request commits. "Schedule" saves an IRB
  Timeline Alert; the `run_due_alerts` scheduler tick creates a run for
  every alert whose `next_run_at` has passed.
- `execute_run` resolves recipients *at send time* (so a scheduled alert
  reflects the data on the day it fires, not the day it was saved) and
  hands one e-mail per student-project to Frappe's Email Queue, which does
  the actual SMTP delivery and retries.

Double-send guards
------------------
- Manual sends carry a client-generated request_id; a repeated request
  (double click, retried POST) returns the existing run.
- A saved alert can't be run again while one of its runs is still
  Queued/Running.
- The scheduler claims an alert under a row lock and advances
  `next_run_at` in the same transaction that creates the run.
- `execute_run` claims its run under a row lock and only proceeds from
  Queued, so a re-enqueued job never processes a run twice.
- All e-mails of a run are queued in one transaction: a crash mid-run
  rolls every one of them back, and the run is marked Failed — never
  "half sent".
"""

import json
import math
import re
from datetime import timedelta

import frappe
from frappe.utils import (
	add_months,
	cint,
	escape_html,
	get_datetime,
	get_url,
	getdate,
	now_datetime,
)
from frappe.utils.data import get_system_timezone

from sirb.sirb.page.irb_admin_console.irb_admin_console import (
	_build_filters_clause,
	get_filter_options,
)
from sirb.sirb_api import irb_timelines
from sirb.sirb_api.irb_timelines import DEADLINE_VARIABLE_NAMES, DEADLINE_VARIABLES

ALERT = "IRB Timeline Alert"
RUN = "IRB Alert Run"

FREQUENCIES = ("Once", "Daily", "Weekly", "Monthly")
ACTIVE_RUN_STATUSES = ("Queued", "Running")

# org_unit: any Academic Organizational Unit, matching everything under it
# (Remind on a timeline uses it for the school the timeline applies to).
LIST_FILTER_KEYS = ("campus", "org_unit", "irb_unit", "academic_year", "irb_cycle", "status", "faculty_mentor")
MAX_INACTIVE_DAYS = 3650
MAX_PICKED_STUDENTS = 500
PREVIEW_ROW_LIMIT = 300

# Runs stuck in these states longer than this are recovered by the
# scheduler (see _recover_stale_runs).
STALE_QUEUED_AFTER = timedelta(minutes=30)
STALE_RUNNING_AFTER = timedelta(hours=2)
ABANDON_QUEUED_AFTER = timedelta(hours=6)
JOB_TIMEOUT = 60 * 60


def _require_admin():
	frappe.only_for("System Manager")


# ---------------------------------------------------------------------------
# Filters and recipients
# ---------------------------------------------------------------------------


def normalize_filters(filters):
	"""Whitelist and clean a filter dict (from the browser or a saved
	alert). Unknown keys are dropped, list filters become lists of
	non-empty strings, and `inactive_days` becomes a bounded int."""
	if isinstance(filters, str):
		try:
			filters = json.loads(filters) if filters.strip() else {}
		except ValueError:
			frappe.throw("Recipient filters are not valid JSON.")
	if not isinstance(filters, dict):
		filters = {}

	if filters.get("mode") == "students":
		# "Specific students": exactly the picked students, nothing else. An
		# empty pick must fail loudly — dropping the key would mean "everyone".
		students = sorted({str(v).strip() for v in (filters.get("student") or []) if v and str(v).strip()})
		if not students:
			frappe.throw("Pick at least one student.")
		if len(students) > MAX_PICKED_STUDENTS:
			frappe.throw(f"Pick at most {MAX_PICKED_STUDENTS} students, or use filters for larger groups.")
		clean = {"mode": "students", "student": students}
		# Which of their projects to e-mail, by status (all when absent).
		statuses = sorted({str(v).strip() for v in (filters.get("status") or []) if v and str(v).strip()})
		if statuses:
			clean["status"] = statuses
		return clean

	clean = {}
	for key in LIST_FILTER_KEYS:
		value = filters.get(key)
		if value in (None, "", []):
			continue
		if not isinstance(value, (list, tuple)):
			value = [value]
		value = sorted({str(v).strip() for v in value if v is not None and str(v).strip()})
		if value:
			clean[key] = value

	inactive_days = cint(filters.get("inactive_days"))
	if inactive_days < 0 or inactive_days > MAX_INACTIVE_DAYS:
		frappe.throw(f"'No update for' must be between 0 and {MAX_INACTIVE_DAYS} days.")
	if inactive_days:
		clean["inactive_days"] = inactive_days
	return clean


def _recipient_rows(filters):
	"""One row per matching student-project membership.

	Same membership rule as the Admin Console (active mapping, or the
	project is Approved), with the Admin Console's own filter clause so a
	given filter means exactly the same thing on both pages.
	"""
	# from_date/to_date are never present — normalize_filters drops them.
	where_extra, params = _build_filters_clause(filters)
	if filters.get("mode") == "students":
		placeholders = []
		for i, student in enumerate(filters["student"]):
			params[f"picked_{i}"] = student
			placeholders.append(f"%(picked_{i})s")
		where_extra += f" and sp.student in ({', '.join(placeholders)})"
	if filters.get("org_unit"):
		# Same nested-set rule as the Campus filter, for any unit type.
		placeholders = []
		for i, unit in enumerate(filters["org_unit"]):
			params[f"org_unit_{i}"] = unit
			placeholders.append(f"%(org_unit_{i})s")
		where_extra += f""" and p.irb_unit in (
			select ouiu.name from `tabIRB Unit` as ouiu
			join `tabAcademic Organizational Unit` as oua on ouiu.ao_unit = oua.name
			join `tabAcademic Organizational Unit` as ouc on oua.lft >= ouc.lft and oua.rgt <= ouc.rgt
			where ouc.name in ({', '.join(placeholders)})
		)"""
	if filters.get("inactive_days"):
		where_extra += " and p.modified <= %(inactive_before)s"
		params["inactive_before"] = now_datetime() - timedelta(days=filters["inactive_days"])

	return frappe.db.sql(
		f"""
		select
			s.name as student, s.full_name as student_name, s.student_id, s.academic_year,
			s.system_user, u.email as user_email, u.enabled as user_enabled,
			p.name as irb_project, p.title as project_title, p.status as project_status,
			p.irb_cycle, p.modified as project_modified,
			iu.ao_name as programme, f.full_name as mentor_name
		from `tabStudent Project Mapping` as sp
		join `tabIRB Project` as p on sp.irb_project = p.name
		join `tabStudent` as s on sp.student = s.name
		join `tabIRB Unit` as iu on p.irb_unit = iu.name
		left join `tabUser` as u on u.name = s.system_user
		left join `tabFaculty` as f on f.name = p.faculty_mentor
		where (sp.status = 'active' or p.status = 'Approved')
		{where_extra}
		order by iu.ao_name asc, s.full_name asc, p.name asc
		""",
		params,
		as_dict=True,
	)


def with_timeline_scope(filters, timeline):
	"""A reminder follows its timeline's *current* unit and cycle, so editing
	the timeline re-targets reminders already scheduled for it. A
	"specific students" reminder is exactly the picked students, unscoped."""
	if not timeline or filters.get("mode") == "students":
		return filters
	scope = frappe.db.get_value(irb_timelines.TIMELINE, timeline, ["ao_unit", "irb_cycle"], as_dict=True)
	if not scope:
		return filters  # a missing timeline is reported by check_link / deadline_context
	scoped = {k: v for k, v in filters.items() if k not in ("org_unit", "irb_cycle")}
	if scope.ao_unit:
		scoped["org_unit"] = [scope.ao_unit]
	if scope.irb_cycle:
		scoped["irb_cycle"] = [scope.irb_cycle]
	return scoped


def resolve_recipients(filters):
	"""Split matching rows into sendable recipients and skipped ones (with
	a reason), deduplicating the same address for the same project."""
	sendable, skipped, seen = [], [], set()
	for row in _recipient_rows(filters):
		email = (row.user_email or "").strip()
		reason = None
		if not row.system_user:
			reason = "No linked user account"
		elif not row.user_enabled:
			reason = "User account is disabled"
		elif not email or "@" not in email:
			reason = "No e-mail address"
		elif (email.lower(), str(row.irb_project)) in seen:
			reason = "Duplicate of another recipient"

		row.email = email
		if reason:
			row.reason = reason
			skipped.append(row)
		else:
			seen.add((email.lower(), str(row.irb_project)))
			sendable.append(row)
	return sendable, skipped


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

TEMPLATE_VARIABLES = [
	("student_name", "Student's full name"),
	("student_id", "Student ID"),
	("academic_year", "Student's academic year"),
	("project_id", "IRB Project ID"),
	("project_label", "Project title in quotes, or \"#<ID>\" while it has no title (fits after \"your IRB project\")"),
	("project_title", "Project title (may be empty)"),
	("project_status", "Current project status"),
	("programme", "Programme / IRB Unit"),
	("irb_cycle", "IRB cycle / batch"),
	("mentor_name", "Faculty mentor's name"),
	("last_updated", "Date the project was last updated"),
	("last_updated_ago", "\"today\", \"yesterday\" or \"14 days ago\""),
	("days_since_update", "Days since the project was last updated (a number)"),
	("project_url", "Link to the project in the portal"),
]


def _project_label(row):
	# Reads naturally after "your IRB project": “Water quality study” / #11.
	# Students often haven't entered a title yet while the proposal is pending.
	title = " ".join((row.project_title or "").split())
	return f"“{title}”" if title else f"#{row.irb_project}"


def _context(row):
	modified = get_datetime(row.project_modified) if row.project_modified else None
	days = max(0, (now_datetime() - modified).days) if modified else 0
	ctx = {
		"student_name": row.student_name or "",
		"student_id": row.student_id or "",
		"academic_year": row.academic_year or "",
		"project_id": str(row.irb_project),
		"project_label": _project_label(row),
		"project_title": row.project_title or "",
		"project_status": row.project_status or "",
		"programme": row.programme or "",
		"irb_cycle": row.irb_cycle or "",
		"mentor_name": row.mentor_name or "",
		"last_updated": frappe.utils.formatdate(modified) if modified else "",
		"last_updated_ago": ("today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago") if modified else "",
		"days_since_update": days,
		"project_url": get_url(f"/sirb/projects/{row.irb_project}"),
	}
	# Names used by the existing status-change templates, so those can be
	# reused here without editing.
	ctx["project_name"] = ctx["project_title"]
	ctx["student_names"] = ctx["student_name"]
	return ctx


def _sample_row():
	return frappe._dict(
		student_name="Sample Student",
		student_id="STU00001",
		academic_year="2026-27",
		irb_project="0",
		project_title="Sample project title",
		project_status="Awaiting proposal completion by student",
		programme="Sample Programme",
		irb_cycle="2026",
		mentor_name="Sample Mentor",
		project_modified=now_datetime() - timedelta(days=14),
	)


def _load_template(name):
	if not name or not frappe.db.exists("Email Template", name):
		frappe.throw("Select a valid e-mail template.")
	tpl = frappe.get_doc("Email Template", name)
	body = tpl.response_ or ""
	if not (tpl.subject or "").strip():
		frappe.throw(f"E-mail template '{name}' has no subject.")
	if not frappe.utils.strip_html(body).strip():
		frappe.throw(f"E-mail template '{name}' has an empty message.")
	return tpl.subject, normalize_editor_html(body)


EDITOR_MARKERS = ("data-list=", "ql-ui", "ql-editor")


def normalize_editor_html(html):
	"""Turn Desk rich-text editor markup into plain e-mail HTML.

	Frappe v15's editor (Quill 2) saves every list as <ol> and marks each
	<li data-list="bullet|ordered">, drawing bullets with its own CSS; e-mail
	clients don't have that CSS, so a bullet list would arrive numbered. It
	also adds <span class="ql-ui"> helpers and a <div class="ql-editor">
	wrapper. Templates without that markup are returned untouched.
	"""
	if not html or not any(m in html for m in EDITOR_MARKERS):
		return html
	from bs4 import BeautifulSoup

	soup = BeautifulSoup(html, "html.parser")
	for helper in soup.select("span.ql-ui"):
		helper.decompose()
	for wrapper in soup.select("div.ql-editor"):
		wrapper.unwrap()
	for lst in soup.find_all(["ol", "ul"]):
		items = lst.find_all("li", recursive=False)
		if not any(li.has_attr("data-list") for li in items):
			continue
		# One Quill list can mix bullet and numbered items: split it into runs.
		runs = []
		for li in items:
			kind = "ol" if li.get("data-list") == "ordered" else "ul"
			del li["data-list"]
			if runs and runs[-1][0] == kind:
				runs[-1][1].append(li)
			else:
				runs.append((kind, [li]))
		for kind, lis in runs:
			new_list = soup.new_tag(kind)
			for li in lis:
				new_list.append(li.extract())
			lst.insert_before(new_list)
		lst.decompose()
	return str(soup)


def _render_string(template, context):
	"""frappe.render_template, minus its path guessing: it treats any
	single-line string ending in .html/.md/… (e.g. a subject "update.html")
	as a template file to load. Same sandbox and safety checks otherwise."""
	from frappe.utils.jinja import get_jenv, safe_render_flags

	if not template:
		return ""
	if ".__" in template:
		frappe.throw("Illegal template")
	with safe_render_flags():
		return get_jenv().from_string(template).render(context)


def _render(subject_tpl, body_tpl, row, deadline=None):
	ctx = _context(row)
	if deadline:
		ctx.update(deadline)
	# The body is HTML: escape interpolated values so a name like "A <B>"
	# can't break the markup. The subject is plain text, so it isn't.
	html_ctx = {k: escape_html(v) if isinstance(v, str) else v for k, v in ctx.items()}
	# Desk's Email Template help suggests {{ doc.fieldname }}; support that
	# spelling too, with the same (escaped / unescaped) values. A plain dict,
	# not frappe._dict: a typo like doc.studnet_name must render blank (Jinja
	# Undefined), not the word "None".
	html_ctx["doc"] = dict(html_ctx)
	ctx["doc"] = dict(ctx)
	subject = _render_string(subject_tpl, ctx).strip()
	body = _render_string(body_tpl, html_ctx)
	# Mail headers can't contain line breaks.
	return " ".join(subject.split()), body


def _check_syntax(subject_tpl, body_tpl):
	"""render_template reports a Jinja syntax error as a raw traceback;
	parse first so the admin gets "Message, line 3: unexpected '}'"."""
	from jinja2 import TemplateSyntaxError

	from frappe.utils.jinja import get_jenv

	for label, tpl in (("Subject", subject_tpl), ("Message", body_tpl)):
		try:
			get_jenv().parse(tpl or "")
		except TemplateSyntaxError as e:
			frappe.throw(f"The e-mail template has an error in its {label}, line {e.lineno}: {e.message}")


def unknown_variables(*templates):
	"""Names a template uses that aren't Timeline Alert variables (usually a
	typo such as {{ studnet_name }}). Frappe's Jinja environment prints an
	unknown variable literally, so the e-mail would show "{{ studnet_name }}":
	previews list these, and every send path refuses the template."""
	from jinja2 import TemplateSyntaxError, meta

	from frappe.utils.jinja import get_jenv

	env = get_jenv()
	known = (
		{name for name, _ in TEMPLATE_VARIABLES}
		| DEADLINE_VARIABLE_NAMES
		| {"project_name", "student_names", "doc"}
		| set(env.globals)
	)
	used = set()
	for tpl in templates:
		try:
			used |= meta.find_undeclared_variables(env.parse(tpl or ""))
		except TemplateSyntaxError:
			pass  # reported separately by _check_syntax
	unknown = sorted(used - known)
	# {{ doc.x }}: check the attribute names too.
	fields = {name for name, _ in TEMPLATE_VARIABLES} | DEADLINE_VARIABLE_NAMES | {"project_name", "student_names"}
	for tpl in templates:
		for attr in re.findall(r"\bdoc\.([A-Za-z_][A-Za-z0-9_]*)", tpl or ""):
			if attr not in fields and f"doc.{attr}" not in unknown:
				unknown.append(f"doc.{attr}")
	return unknown


def _check_variables(subject_tpl, body_tpl):
	unknown = unknown_variables(subject_tpl, body_tpl)
	if unknown:
		names = ", ".join("{{ %s }}" % u for u in unknown)
		frappe.throw(
			f"The e-mail template uses unknown variables: {names}. Students would see them as-is, "
			"so fix or remove them in the template first."
		)


def validate_template_for_sending(subject_tpl, body_tpl, has_deadline=False):
	_check_syntax(subject_tpl, body_tpl)
	_check_variables(subject_tpl, body_tpl)
	if not has_deadline and irb_timelines.uses_deadline_variables(subject_tpl, body_tpl):
		frappe.throw(
			"This template uses deadline variables such as {{ deadline_date }}, but the alert isn't linked to a "
			"timeline activity. Use Remind on the Timelines tab, or pick a template without deadline variables."
		)


def _render_or_throw(subject_tpl, body_tpl, row, deadline=None):
	_check_syntax(subject_tpl, body_tpl)
	try:
		return _render(subject_tpl, body_tpl, row, deadline)
	except Exception as e:
		# render_template's own throw queues a traceback message; replace it
		# with the last line of that traceback (the actual error).
		frappe.clear_messages()
		frappe.throw(f"The e-mail template could not be rendered: {_error_line(e)}")


# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------


def _outgoing_email_configured():
	if frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}):
		return True
	# Frappe also falls back to mail settings in site_config.json.
	return bool(frappe.conf.get("mail_server"))


def _scheduler_active():
	from frappe.utils.scheduler import is_scheduler_inactive

	return not is_scheduler_inactive(verbose=False)


def _email_muted():
	return bool(frappe.flags.mute_emails or frappe.conf.get("mute_emails"))


# ---------------------------------------------------------------------------
# Schedule maths
# ---------------------------------------------------------------------------

INTERVAL_DAYS = {"Daily": 1, "Weekly": 7}


def compute_next_run(frequency, start_at, end_date=None, after=None):
	"""First scheduled slot strictly after `after` (default: now), or None
	when the schedule is finished.

	Slots are always counted from `start_at` (start + k*interval), so a
	monthly alert started on the 31st fires on the last day of shorter
	months and returns to the 31st afterwards instead of drifting to the
	28th; and missed slots (scheduler down) are skipped, not replayed.
	"""
	start_at = get_datetime(start_at)
	after = get_datetime(after) if after else now_datetime()
	end = getdate(end_date) if end_date else None

	if frequency == "Once":
		candidate = start_at if start_at > after else None
	elif frequency in INTERVAL_DAYS:
		if start_at > after:
			candidate = start_at
		else:
			step = timedelta(days=INTERVAL_DAYS[frequency])
			k = math.floor((after - start_at) / step) + 1
			candidate = start_at + k * step
			if candidate <= after:  # float rounding guard
				candidate += step
	elif frequency == "Monthly":
		if start_at > after:
			candidate = start_at
		else:
			months = (after.year - start_at.year) * 12 + (after.month - start_at.month)
			k = max(months, 0)
			candidate = get_datetime(add_months(start_at, k))
			while candidate <= after:
				k += 1
				candidate = get_datetime(add_months(start_at, k))
	else:
		frappe.throw(f"Frequency must be one of: {', '.join(FREQUENCIES)}.")

	if candidate and end and candidate.date() > end:
		return None
	return candidate


def validate_alert(doc):
	"""Called from IRBTimelineAlert.validate — shared by the portal and Desk."""
	doc.alert_name = (doc.alert_name or "").strip()
	if not doc.alert_name:
		frappe.throw("Alert name is required.")
	if doc.frequency not in FREQUENCIES:
		frappe.throw(f"Frequency must be one of: {', '.join(FREQUENCIES)}.")
	if not doc.start_at:
		frappe.throw("Choose when the alert should first run.")

	subject_tpl, body_tpl = _load_template(doc.email_template)
	doc.timeline, doc.milestone = irb_timelines.check_link(doc.timeline, doc.milestone)
	if cint(doc.enabled):
		# Only an enabled alert must have a sendable template: pausing an
		# alert whose template was broken later must always be possible.
		deadline = irb_timelines.deadline_context(doc.timeline, doc.milestone) if doc.timeline else None
		validate_template_for_sending(subject_tpl, body_tpl, has_deadline=bool(deadline))
		_render_or_throw(subject_tpl, body_tpl, _sample_row(), deadline)

	filters = normalize_filters(doc.filters)
	doc.filters = json.dumps(filters, sort_keys=True)

	if doc.end_date and getdate(doc.end_date) < get_datetime(doc.start_at).date():
		frappe.throw("'Stop after' can't be before the first run.")

	schedule_changed = doc.is_new() or any(
		doc.has_value_changed(f) for f in ("enabled", "frequency", "start_at", "end_date")
	)
	if not cint(doc.enabled):
		doc.next_run_at = None
	elif schedule_changed or not doc.next_run_at:
		next_run = compute_next_run(doc.frequency, doc.start_at, doc.end_date)
		if not next_run:
			if doc.frequency == "Once":
				frappe.throw("The run time is in the past. Pick a future time, or use Send now instead.")
			frappe.throw("This schedule has no runs left before its 'Stop after' date.")
		doc.next_run_at = next_run


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


def _job_id(run_name):
	return f"sirb_alert_run::{run_name}"


def _enqueue_run(run_name):
	frappe.enqueue(
		"sirb.sirb_api.timeline_alerts.execute_run",
		queue="long",
		timeout=JOB_TIMEOUT,
		enqueue_after_commit=True,
		job_id=_job_id(run_name),
		deduplicate=True,
		run_name=run_name,
	)


def _create_run(
	*, trigger, filters, email_template, alert=None, alert_name=None, request_id=None, timeline=None, milestone=None
):
	label = None
	if timeline:
		try:
			label = irb_timelines.deadline_label(timeline, milestone)
		except frappe.ValidationError:
			# Activity removed after scheduling: execute_run fails the run
			# with the reason instead of it never starting.
			frappe.clear_messages()
	run = frappe.get_doc(
		{
			"doctype": RUN,
			"alert": alert,
			"alert_name": alert_name or "Ad-hoc alert",
			"trigger": trigger,
			"triggered_by": frappe.session.user,
			"status": "Queued",
			"email_template": email_template,
			"filters": json.dumps(filters, sort_keys=True),
			"request_id": request_id,
			"timeline": timeline,
			"milestone": milestone,
			"deadline_label": label,
		}
	)
	run.insert(ignore_permissions=True)
	_enqueue_run(run.name)
	return run


def _set_run(run_name, **values):
	frappe.db.set_value(RUN, run_name, values, update_modified=True)


def _notify(run_name):
	run = frappe.db.get_value(
		RUN, run_name, ["name", "status", "sent_count", "skipped_count", "failed_count", "triggered_by"], as_dict=True
	)
	if run and run.triggered_by:
		frappe.publish_realtime("sirb_alert_run_update", run, user=run.triggered_by)


def execute_run(run_name):
	"""Background job: queue the e-mails for one IRB Alert Run."""
	# Claim the run: only a Queued run is processed, under a row lock, so a
	# duplicate job for the same run exits here.
	status = frappe.db.get_value(RUN, run_name, "status", for_update=True)
	if status != "Queued":
		frappe.db.rollback()
		return
	_set_run(run_name, status="Running", started_at=now_datetime())
	frappe.db.commit()

	try:
		run = frappe.get_doc(RUN, run_name)
		if not _outgoing_email_configured():
			raise frappe.ValidationError("No outgoing e-mail account is configured, so nothing was sent.")

		subject_tpl, body_tpl = _load_template(run.email_template)
		# The deadline's *current* dates, so a moved deadline moves the text too.
		deadline = irb_timelines.deadline_context(run.timeline, run.milestone) if run.timeline else None
		validate_template_for_sending(subject_tpl, body_tpl, has_deadline=bool(deadline))
		filters = with_timeline_scope(normalize_filters(run.filters), run.timeline)
		sendable, skipped = resolve_recipients(filters)

		rows, sent, failed = [], 0, 0
		for r in sendable:
			frappe.db.savepoint("alert_recipient")
			try:
				subject, body = _render(subject_tpl, body_tpl, r, deadline)
				frappe.sendmail(
					recipients=[r.email],
					subject=subject,
					message=body,
					# Tag each e-mail with its run, so Email Queue shows exactly
					# which alert sent it and the Timeline Alerts workspace can
					# report real delivery status (Sent / Error) per run.
					reference_doctype=RUN,
					reference_name=run_name,
					# Required academic notices: no unsubscribe footer,
					# and nobody opts themselves out of deadlines.
					add_unsubscribe_link=0,
					delayed=True,
				)
				sent += 1
				rows.append(_recipient_row(r, "Queued"))
			except Exception as e:
				frappe.db.rollback(save_point="alert_recipient")
				failed += 1
				frappe.clear_messages()
				rows.append(_recipient_row(r, "Failed", _error_line(e)))
		rows.extend(_recipient_row(r, "Skipped", r.reason) for r in skipped)

		if not sendable:
			final = "No recipients"
		elif failed:
			final = "Completed with errors"
		else:
			final = "Completed"

		run.reload()
		run.filters = json.dumps(filters, sort_keys=True)  # what was actually used
		run.set("recipients", rows)
		run.total_recipients = len(sendable) + len(skipped)
		run.sent_count = sent
		run.skipped_count = len(skipped)
		run.failed_count = failed
		run.status = final
		run.finished_at = now_datetime()
		run.flags.ignore_permissions = True
		run.save()
		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		message = frappe.utils.strip_html(str(e)) or type(e).__name__
		if not isinstance(e, frappe.ValidationError):
			frappe.log_error(title=f"Timeline alert run {run_name} failed", reference_doctype=RUN, reference_name=run_name)
			message = f"Unexpected error: {message}"
		frappe.clear_messages()
		_set_run(run_name, status="Failed", error=message[:2000], finished_at=now_datetime())
		frappe.db.commit()
	_notify(run_name)


def _error_line(e):
	lines = [ln.strip() for ln in frappe.utils.strip_html(str(e)).splitlines() if ln.strip()]
	return (lines[-1] if lines else type(e).__name__)[:500]


def _recipient_row(r, status, reason=None):
	return {
		"student": r.student,
		"student_name": r.student_name,
		"email": r.email or None,
		"irb_project": r.irb_project,
		"status": status,
		"reason": reason,
	}


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def run_due_alerts():
	"""Scheduler tick (hooks.py, every 5 minutes)."""
	now = now_datetime()
	due = frappe.get_all(ALERT, filters={"enabled": 1, "next_run_at": ("<=", now)}, pluck="name")
	for name in due:
		try:
			_fire_alert(name, now)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Timeline alert {name} could not be started", reference_doctype=ALERT, reference_name=name)
			frappe.db.commit()

	try:
		_recover_stale_runs(now)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Timeline alerts: stale run recovery failed")
		frappe.db.commit()


def _fire_alert(name, now):
	alert = frappe.db.get_value(
		ALERT,
		name,
		[
			"name", "alert_name", "enabled", "email_template", "filters", "frequency",
			"start_at", "end_date", "next_run_at", "timeline", "milestone",
		],
		as_dict=True,
		for_update=True,
	)
	# Re-check under the lock: another tick or an edit may have got here first.
	if not alert or not cint(alert.enabled) or not alert.next_run_at or get_datetime(alert.next_run_at) > now:
		return

	next_run = compute_next_run(alert.frequency, alert.start_at, alert.end_date, after=now)
	updates = {"last_run_at": now, "next_run_at": next_run}
	if not next_run:
		updates["enabled"] = 0

	if _has_active_run(name):
		# Previous run still going (huge batch or a stuck worker): skip this
		# slot rather than stacking a second send behind it.
		frappe.db.set_value(ALERT, name, updates, update_modified=False)
		return

	if alert.timeline and not cint(frappe.db.get_value(irb_timelines.TIMELINE, alert.timeline, "is_active")):
		# Timeline switched off: skip this slot (the schedule still moves on,
		# so reactivating it doesn't release a backlog of old reminders).
		frappe.db.set_value(ALERT, name, updates, update_modified=False)
		return

	run = _create_run(
		trigger="Scheduled",
		filters=normalize_filters(alert.filters),
		email_template=alert.email_template,
		alert=name,
		alert_name=alert.alert_name,
		timeline=alert.timeline,
		milestone=alert.milestone,
	)
	updates["last_run"] = run.name
	frappe.db.set_value(ALERT, name, updates, update_modified=False)


def _recover_stale_runs(now):
	from frappe.utils.background_jobs import is_job_enqueued

	# Queued but no job in RQ (worker restarted, Redis flushed): enqueue
	# again. execute_run's Queued-only claim makes this safe to repeat.
	for run in frappe.get_all(
		RUN, filters={"status": "Queued", "creation": ("<", now - STALE_QUEUED_AFTER)}, fields=["name", "creation"]
	):
		if is_job_enqueued(_job_id(run.name)):
			continue
		if get_datetime(run.creation) < now - ABANDON_QUEUED_AFTER:
			# Re-enqueued for hours and never started: stop retrying.
			_set_run(
				run.name,
				status="Failed",
				finished_at=now,
				error="The run never started (background workers unavailable). Nothing was sent; start it again.",
			)
		else:
			_enqueue_run(run.name)

	# Running long past the job timeout: the worker died mid-run and its
	# transaction (with every e-mail it queued) was rolled back.
	for run in frappe.get_all(
		RUN, filters={"status": "Running", "started_at": ("<", now - STALE_RUNNING_AFTER)}, pluck="name"
	):
		_set_run(
			run,
			status="Failed",
			finished_at=now,
			error="The run was interrupted before it finished. No e-mails from it were sent; start it again.",
		)


def _has_active_run(alert_name):
	return bool(frappe.db.exists(RUN, {"alert": alert_name, "status": ("in", ACTIVE_RUN_STATUSES)}))


# ---------------------------------------------------------------------------
# Whitelisted API for the portal page
# ---------------------------------------------------------------------------


def _parse(data):
	if isinstance(data, str):
		data = frappe.parse_json(data)
	return frappe._dict(data or {})


def _alert_rows():
	alerts = frappe.get_all(
		ALERT,
		fields=[
			"name", "alert_name", "enabled", "email_template", "filters", "frequency",
			"start_at", "end_date", "next_run_at", "last_run_at", "last_run", "modified",
			"timeline", "milestone",
		],
		order_by="enabled desc, next_run_at asc, modified desc",
	)
	run_names = [a.last_run for a in alerts if a.last_run]
	last_runs = (
		{r.name: r for r in frappe.get_all(RUN, filters={"name": ("in", run_names)}, fields=["name", "status", "sent_count"])}
		if run_names
		else {}
	)
	active = set(
		frappe.get_all(RUN, filters={"status": ("in", ACTIVE_RUN_STATUSES), "alert": ("is", "set")}, pluck="alert")
	)
	inactive_timelines = set(frappe.get_all(irb_timelines.TIMELINE, filters={"is_active": 0}, pluck="name"))
	for a in alerts:
		a.filters = normalize_filters(a.filters)
		lr = last_runs.get(a.last_run)
		a.last_run_status = lr.status if lr else None
		a.last_run_sent = lr.sent_count if lr else None
		a.is_running = a.name in active
		a.timeline_inactive = bool(a.timeline and a.timeline in inactive_timelines)
		a.deadline_label = None
		if a.timeline:
			try:
				a.deadline_label = irb_timelines.deadline_label(a.timeline, a.milestone)
			except frappe.ValidationError:
				frappe.clear_messages()
				a.deadline_label = "Linked activity no longer exists"
	return alerts


def _student_search_rows(where, params, limit):
	"""Students who can receive an alert (same membership rule as
	_recipient_rows), one row per student with their projects summarised."""
	return frappe.db.sql(
		f"""
		select s.name as student, s.full_name as student_name, s.student_id, s.academic_year,
			u.email as email, ifnull(u.enabled, 0) as user_enabled,
			group_concat(distinct iu.ao_name order by iu.ao_name separator ', ') as programme,
			count(distinct p.name) as project_count
		from `tabStudent Project Mapping` as sp
		join `tabIRB Project` as p on sp.irb_project = p.name
		join `tabStudent` as s on sp.student = s.name
		join `tabIRB Unit` as iu on p.irb_unit = iu.name
		left join `tabUser` as u on u.name = s.system_user
		where (sp.status = 'active' or p.status = 'Approved') and {where}
		group by s.name
		order by s.full_name asc
		limit {int(limit)}
		""",
		params,
		as_dict=True,
	)


@frappe.whitelist()
def search_students(txt="", limit=20):
	"""Picker search by name, student ID or e-mail."""
	_require_admin()
	txt = (txt or "").strip()
	if len(txt) < 2:
		return []
	like = "%" + txt.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
	return _student_search_rows(
		"(s.full_name like %(q)s or s.student_id like %(q)s or u.email like %(q)s or s.name like %(q)s)",
		{"q": like},
		min(max(cint(limit), 1), 50),
	)


@frappe.whitelist()
def get_student_labels(names=None):
	"""Picker rows for already-chosen students (editing a saved alert)."""
	_require_admin()
	names = frappe.parse_json(names) if isinstance(names, str) else names
	names = [str(n) for n in (names or []) if n][:MAX_PICKED_STUDENTS]
	if not names:
		return []
	params = {f"n{i}": n for i, n in enumerate(names)}
	return _student_search_rows(f"s.name in ({', '.join('%(' + k + ')s' for k in params)})", params, len(names))


@frappe.whitelist()
def get_page_data():
	"""Everything the page needs on load, in one round trip."""
	_require_admin()
	return {
		"filter_options": get_filter_options(),
		"templates": _template_options(),
		"alerts": _alert_rows(),
		"timelines": irb_timelines.timeline_rows(),
		"units": irb_timelines.unit_options(),
		"environment": {
			"email_configured": _outgoing_email_configured(),
			"scheduler_active": _scheduler_active(),
			"email_muted": _email_muted(),
			"timezone": get_system_timezone(),
			"server_now": now_datetime(),
		},
	}


@frappe.whitelist()
def get_alerts():
	_require_admin()
	return _alert_rows()


@frappe.whitelist()
def preview_recipients(filters=None, timeline=None):
	_require_admin()
	filters = with_timeline_scope(normalize_filters(filters), timeline)
	# Counts per status come from the same filters *without* the status
	# filter, so the status checkboxes can show what each one would add.
	statuses = set(filters.pop("status", None) or [])
	sendable, skipped = resolve_recipients(filters)
	status_counts = {}
	for r in sendable:
		status_counts[r.project_status] = status_counts.get(r.project_status, 0) + 1
	if statuses:
		sendable = [r for r in sendable if r.project_status in statuses]
		skipped = [r for r in skipped if r.project_status in statuses]

	def slim(r):
		return {
			"student": r.student,
			"student_name": r.student_name,
			"student_id": r.student_id,
			"email": r.email,
			"irb_project": r.irb_project,
			"project_title": r.project_title,
			"project_status": r.project_status,
			"programme": r.programme,
			"project_modified": r.project_modified,
			"reason": r.get("reason"),
		}

	return {
		"sendable_count": len(sendable),
		"skipped_count": len(skipped),
		"unique_students": len({r.student for r in sendable}),
		"sendable": [slim(r) for r in sendable[:PREVIEW_ROW_LIMIT]],
		"skipped": [slim(r) for r in skipped[:PREVIEW_ROW_LIMIT]],
		"row_limit": PREVIEW_ROW_LIMIT,
		"status_counts": status_counts,
	}


@frappe.whitelist()
def preview_email(email_template, filters=None, timeline=None, milestone=None):
	"""Render the template for the first matching recipient (or sample
	data when nothing matches), with the linked deadline if any."""
	_require_admin()
	subject_tpl, body_tpl = _load_template(email_template)
	sendable, _ = resolve_recipients(with_timeline_scope(normalize_filters(filters), timeline))
	row = sendable[0] if sendable else _sample_row()
	deadline, needs_deadline = _preview_deadline(subject_tpl, body_tpl, timeline, milestone)
	subject, body = _render_or_throw(subject_tpl, body_tpl, row, deadline)
	return {
		"subject": subject,
		"html": body,
		"recipient": {"student_name": row.student_name, "email": row.get("email")} if sendable else None,
		"unknown_variables": unknown_variables(subject_tpl, body_tpl),
		"needs_deadline": needs_deadline,
	}


def _preview_deadline(subject_tpl, body_tpl, timeline=None, milestone=None):
	"""(deadline context, needs_deadline). Without a linked activity, a
	template that uses deadline variables previews with sample values and
	is flagged, since sending it is refused."""
	timeline, milestone = irb_timelines.check_link(timeline, milestone)
	if timeline:
		return irb_timelines.deadline_context(timeline, milestone), False
	if irb_timelines.uses_deadline_variables(subject_tpl, body_tpl):
		return dict(irb_timelines.SAMPLE_DEADLINE), True
	return None, False


@frappe.whitelist(methods=["POST"])
def preview_template_draft(subject=None, response=None, use_html=0, response_html=None):
	"""Render unsaved Email Template content (the Desk editor's "Preview as
	Timeline Alert" button) for the first student with a project."""
	_require_admin()
	body_tpl = normalize_editor_html((response_html if cint(use_html) else response) or "")
	subject_tpl = subject or ""
	if not subject_tpl.strip():
		frappe.throw("Add a subject first.")
	if not frappe.utils.strip_html(body_tpl).strip():
		frappe.throw("Add a message first.")
	sendable, _ = resolve_recipients({})
	row = sendable[0] if sendable else _sample_row()
	deadline, needs_deadline = _preview_deadline(subject_tpl, body_tpl)
	subject_out, body = _render_or_throw(subject_tpl, body_tpl, row, deadline)
	return {
		"subject": subject_out,
		"html": body,
		"recipient": {"student_name": row.student_name, "email": row.get("email")} if sendable else None,
		"unknown_variables": unknown_variables(subject_tpl, body_tpl),
		"needs_deadline": needs_deadline,
	}


@frappe.whitelist()
def get_template_editor_info(name=None):
	"""What the Desk Email Template form shows System Managers: the
	variables, and which scheduled alerts use this template."""
	_require_admin()
	from sirb.sirb_api.alert_templates import DEFAULT_TEMPLATE_NAMES
	from sirb.sirb_api.status_email_templates import STATUS_EMAIL_VARIABLES, get_status_email_templates

	return {
		"variables": [{"name": n, "description": d} for n, d in TEMPLATE_VARIABLES]
		+ [{"name": n, "description": f"{d} — only for alerts linked to a timeline activity"} for n, d in DEADLINE_VARIABLES],
		"used_by": frappe.get_all(ALERT, filters={"email_template": name}, pluck="alert_name") if name else [],
		"is_default": name in DEFAULT_TEMPLATE_NAMES,
		# Status e-mails get different variables from Timeline Alerts.
		"status_email_variables": [{"name": n, "description": d} for n, d in STATUS_EMAIL_VARIABLES]
		if name in {t["name"] for t in get_status_email_templates()}
		else None,
	}


def _template_options():
	"""Timeline Alert templates first, then every other template."""
	rows = frappe.get_all("Email Template", fields=["name", "subject"], order_by="name asc")
	return sorted(rows, key=lambda r: (not r.name.startswith("Timeline Alert"), r.name.lower()))


@frappe.whitelist()
def get_templates():
	_require_admin()
	return _template_options()


def _check_can_send():
	if not _outgoing_email_configured():
		frappe.throw("No outgoing e-mail account is configured. Set one up in Desk (Email Account) first.")


@frappe.whitelist(methods=["POST"])
def send_now(email_template, filters=None, request_id=None, timeline=None, milestone=None):
	_require_admin()
	request_id = (request_id or "").strip()[:140] or None
	if request_id:
		existing = frappe.db.get_value(RUN, {"request_id": request_id}, "name")
		if existing:
			return existing

	_check_can_send()
	subject_tpl, body_tpl = _load_template(email_template)
	timeline, milestone = irb_timelines.check_link(timeline, milestone)
	filters = normalize_filters(filters)
	sendable, _ = resolve_recipients(with_timeline_scope(filters, timeline))
	if not sendable:
		frappe.throw("No students with an e-mail address match these filters.")
	deadline = irb_timelines.deadline_context(timeline, milestone) if timeline else None
	validate_template_for_sending(subject_tpl, body_tpl, has_deadline=bool(deadline))
	_render_or_throw(subject_tpl, body_tpl, sendable[0], deadline)

	try:
		return _create_run(
			trigger="Manual",
			filters=filters,
			email_template=email_template,
			request_id=request_id,
			timeline=timeline,
			milestone=milestone,
		).name
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		# A concurrent identical request won the race (request_id is unique).
		frappe.db.rollback()
		frappe.clear_messages()
		return frappe.db.get_value(RUN, {"request_id": request_id}, "name")


@frappe.whitelist(methods=["POST"])
def save_alert(data):
	"""Create or update a scheduled alert."""
	_require_admin()
	data = _parse(data)

	doc = frappe.get_doc(ALERT, data.name) if data.name else frappe.new_doc(ALERT)
	doc.alert_name = data.alert_name
	doc.email_template = data.email_template
	doc.filters = json.dumps(normalize_filters(data.filters), sort_keys=True)
	doc.frequency = data.frequency
	# <input type="datetime-local"> sends "YYYY-MM-DDTHH:MM".
	doc.start_at = get_datetime(str(data.start_at).replace("T", " ")) if data.start_at else None
	doc.end_date = data.end_date or None
	doc.enabled = 1 if cint(data.enabled if data.enabled is not None else 1) else 0
	doc.timeline = data.timeline or None
	doc.milestone = data.milestone or None
	doc.save()
	return doc.name


@frappe.whitelist(methods=["POST"])
def set_alert_enabled(name, enabled):
	_require_admin()
	doc = frappe.get_doc(ALERT, name)
	doc.enabled = 1 if cint(enabled) else 0
	doc.save()
	return {"enabled": doc.enabled, "next_run_at": doc.next_run_at}


@frappe.whitelist(methods=["POST"])
def run_alert_now(name):
	"""Send a saved alert immediately, without touching its schedule."""
	_require_admin()
	alert = frappe.db.get_value(
		ALERT, name, ["name", "alert_name", "email_template", "filters", "timeline", "milestone"], as_dict=True, for_update=True
	)
	if not alert:
		frappe.throw("This alert no longer exists.")
	if _has_active_run(name):
		frappe.throw("This alert is already being sent. Wait for that run to finish.")
	_check_can_send()
	if alert.timeline:
		irb_timelines.deadline_context(alert.timeline, alert.milestone)  # still exists?
	validate_template_for_sending(*_load_template(alert.email_template), has_deadline=bool(alert.timeline))
	run = _create_run(
		trigger="Manual",
		filters=normalize_filters(alert.filters),
		email_template=alert.email_template,
		alert=name,
		alert_name=alert.alert_name,
		timeline=alert.timeline,
		milestone=alert.milestone,
	)
	frappe.db.set_value(ALERT, name, {"last_run": run.name, "last_run_at": now_datetime()}, update_modified=False)
	return run.name


@frappe.whitelist(methods=["POST"])
def delete_alert(name):
	_require_admin()
	if not frappe.db.exists(ALERT, name):
		frappe.throw("This alert no longer exists.")
	if _has_active_run(name):
		frappe.throw("This alert is being sent right now. Delete it after the run finishes.")
	# Keep the run history (it carries the alert name as a snapshot) but
	# drop the link, which would otherwise block the delete.
	frappe.db.set_value(ALERT, name, "last_run", None, update_modified=False)
	frappe.db.sql(f"update `tab{RUN}` set alert = null where alert = %s", name)
	frappe.delete_doc(ALERT, name)


@frappe.whitelist()
def get_runs(limit=50, alert=None):
	_require_admin()
	filters = {"alert": alert} if alert else {}
	return frappe.get_all(
		RUN,
		filters=filters,
		fields=[
			"name", "alert", "alert_name", "trigger", "triggered_by", "status", "email_template", "deadline_label",
			"total_recipients", "sent_count", "skipped_count", "failed_count",
			"creation", "started_at", "finished_at", "error",
		],
		order_by="creation desc",
		limit_page_length=min(max(cint(limit), 1), 200),
	)


@frappe.whitelist()
def get_run(name):
	_require_admin()
	if not frappe.db.exists(RUN, name):
		frappe.throw("This run no longer exists.")
	run = frappe.get_doc(RUN, name).as_dict()
	run.filters = normalize_filters(run.filters)
	run.triggered_by_name = frappe.utils.get_fullname(run.triggered_by) if run.triggered_by else None
	run.recipients = [
		{k: r.get(k) for k in ("idx", "student", "student_name", "email", "irb_project", "status", "reason")}
		for r in run.recipients
	]
	return run


# ---------------------------------------------------------------------------
# Workspace charts (Dashboard Chart Sources "Timeline Alert Run Status" and
# "Timeline Alert E-mail Delivery")
# ---------------------------------------------------------------------------

# Each bucket is its own dataset of a single-bar group, returned in this fixed
# order even when 0: chart colours are assigned per dataset by position, so the
# `colors` list in each chart's custom_options (dashboard_chart/*.json) must
# stay in the same order. A status outside every bucket lands in a trailing
# "Other" dataset (last colour). A Percentage/Pie chart can't be used: those
# draw a broken SVG path for 0-value slices, and dropping the 0s would shift
# every colour onto the wrong status.
RUN_STATUS_BUCKETS = [
	("Completed", ("Completed",)),
	("With errors", ("Completed with errors",)),  # legend slots fit ~15 characters
	("Failed", ("Failed",)),
	("No recipients", ("No recipients",)),
	("In progress", ("Queued", "Running")),
]
DELIVERY_BUCKETS = [
	("Delivered", ("Sent", "Partially Sent")),
	("Waiting to send", ("Not Sent", "Sending")),
	("Failed", ("Error",)),
]
CHART_PERIODS = ("Last 7 Days", "Last 30 Days", "Last 90 Days")


def _chart_period(filters):
	filters = frappe.parse_json(filters) if filters else {}
	period = (filters or {}).get("period") if isinstance(filters, dict) else None
	return (period if period in CHART_PERIODS else "Last 30 Days").lower()


def _status_breakdown(doctype, filters, buckets, period_label):
	counts = dict(
		frappe.get_all(doctype, filters=filters, fields=["status", "count(name)"], group_by="status", as_list=True)
	)
	if not sum(counts.values()):
		return None  # the chart widget shows its "No Data" state

	datasets = [{"name": label, "values": [sum(counts.pop(s, 0) for s in statuses)]} for label, statuses in buckets]
	other = sum(counts.values())
	if other:
		datasets.append({"name": "Other", "values": [other]})
	return {"labels": [period_label], "datasets": datasets}


@frappe.whitelist()
def get_run_status_chart(filters=None, **kwargs):
	_require_admin()
	period = _chart_period(filters)
	return _status_breakdown(RUN, [[RUN, "creation", "Timespan", period]], RUN_STATUS_BUCKETS, period.title())


@frappe.whitelist()
def get_email_delivery_chart(filters=None, **kwargs):
	_require_admin()
	period = _chart_period(filters)
	return _status_breakdown(
		"Email Queue",
		[["Email Queue", "reference_doctype", "=", RUN], ["Email Queue", "creation", "Timespan", period]],
		DELIVERY_BUCKETS,
		period.title(),
	)
