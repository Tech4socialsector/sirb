# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""IRB Timelines: the review calendar each school publishes for a cycle
("Last date for submission of IRB forms — 25 July 2026", …), kept as an
IRB Timeline with one IRB Timeline Milestone row per activity and shown as a
table on the portal's Timeline Alerts page.

A timeline activity can be linked to an alert ("Remind"). The alert's
e-mails then get the deadline variables below, filled from the activity's
*current* dates when each e-mail is rendered — so moving a deadline also
moves what already-scheduled reminders say.
"""

import json
import re

import frappe
from frappe.utils import cint, formatdate, getdate, nowdate

TIMELINE = "IRB Timeline"
MILESTONE = "IRB Timeline Milestone"
ALERT = "IRB Timeline Alert"
AOU = "Academic Organizational Unit"

DEADLINE_VARIABLES = [
	("deadline_activity", 'The linked timeline activity, e.g. "Last date for submission of IRB forms"'),
	("deadline_date", "Its date (the end date when it is a date range)"),
	("deadline_time", 'Its time or note, e.g. "6:00 PM" (may be empty)'),
	("deadline_when", '"today", "tomorrow", "in 5 days" or "2 days ago"'),
	("days_to_deadline", "Days until the deadline (a number; negative once it has passed)"),
	("timeline_name", 'The timeline, e.g. "School of Development – August 2026"'),
]
DEADLINE_VARIABLE_NAMES = {name for name, _ in DEADLINE_VARIABLES}

MAX_MILESTONES = 50


def _require_admin():
	frappe.only_for("System Manager")


def _status_list():
	from sirb.sirb.page.irb_admin_console.irb_admin_console import STATUS_LIST

	return STATUS_LIST


def parse_statuses(value):
	"""Remind statuses from JSON / list, keeping only real project statuses, in workflow order."""
	if isinstance(value, str):
		try:
			value = json.loads(value) if value.strip() else []
		except ValueError:
			value = []
	chosen = {str(v) for v in (value or []) if v}
	return [s for s in _status_list() if s in chosen]


def deadline_of(row):
	"""The day an activity is due: the end of a range, else its date."""
	return getdate(row.get("end_date") or row.get("start_date"))


def _when(days):
	if days == 0:
		return "today"
	if days == 1:
		return "tomorrow"
	if days == -1:
		return "yesterday"
	return f"in {days} days" if days > 0 else f"{-days} days ago"


def _milestone(timeline, milestone):
	row = frappe.db.get_value(
		MILESTONE,
		{"name": milestone, "parent": timeline, "parenttype": TIMELINE},
		["name", "activity", "start_date", "end_date", "time_note"],
		as_dict=True,
	)
	if not row:
		frappe.throw(
			"The timeline activity this alert reminds about no longer exists. "
			"Link the alert to another activity (Timelines → Remind) or use a template without deadline variables."
		)
	return row


def deadline_context(timeline, milestone, today=None):
	"""Template variables for a linked activity."""
	row = _milestone(timeline, milestone)
	due = deadline_of(row)
	days = (due - getdate(today or nowdate())).days
	return {
		"deadline_activity": row.activity or "",
		"deadline_date": formatdate(due),
		"deadline_time": row.time_note or "",
		"deadline_when": _when(days),
		"days_to_deadline": days,
		"timeline_name": frappe.db.get_value(TIMELINE, timeline, "timeline_name") or "",
	}


def deadline_label(timeline, milestone):
	row = _milestone(timeline, milestone)
	return f"{row.activity} ({formatdate(deadline_of(row))})"[:140]


SAMPLE_DEADLINE = {
	"deadline_activity": "Last date for submission of IRB forms",
	"deadline_date": "25-07-2026",
	"deadline_time": "6:00 PM",
	"deadline_when": "in 5 days",
	"days_to_deadline": 5,
	"timeline_name": "Sample timeline",
}


def uses_deadline_variables(*templates):
	from jinja2 import TemplateSyntaxError, meta

	from frappe.utils.jinja import get_jenv

	env = get_jenv()
	used = set()
	for tpl in templates:
		try:
			used |= meta.find_undeclared_variables(env.parse(tpl or ""))
		except TemplateSyntaxError:
			pass
		used |= set(re.findall(r"\bdoc\.([A-Za-z_][A-Za-z0-9_]*)", tpl or ""))
	return bool(used & DEADLINE_VARIABLE_NAMES)


def check_link(timeline, milestone):
	"""A deadline link is both fields or neither, and must exist."""
	timeline, milestone = (timeline or "").strip() or None, (milestone or "").strip() or None
	if bool(timeline) != bool(milestone):
		frappe.throw("Pick a timeline activity to link, or remove the link.")
	if timeline:
		_milestone(timeline, milestone)
	return timeline, milestone


# ---------------------------------------------------------------------------
# Validation (IRBTimeline.validate / on_trash)
# ---------------------------------------------------------------------------


def validate_timeline(doc):
	doc.timeline_name = (doc.timeline_name or "").strip()
	if not doc.timeline_name:
		frappe.throw("Timeline name is required.")
	doc.irb_cycle = (doc.irb_cycle or "").strip() or None
	if doc.ao_unit and not frappe.db.exists(AOU, doc.ao_unit):
		frappe.throw("The selected unit no longer exists.")
	if not doc.milestones:
		frappe.throw("Add at least one activity.")
	if len(doc.milestones) > MAX_MILESTONES:
		frappe.throw(f"A timeline can have at most {MAX_MILESTONES} activities.")

	for i, row in enumerate(doc.milestones, start=1):
		row.activity = " ".join((row.activity or "").split())
		if not row.activity:
			frappe.throw(f"Row {i}: the activity is required.")
		if not row.start_date:
			frappe.throw(f"Row {i} ({row.activity}): the date is required.")
		if row.end_date and getdate(row.end_date) < getdate(row.start_date):
			frappe.throw(f"Row {i} ({row.activity}): 'To' is before the start date.")
		row.time_note = (row.time_note or "").strip() or None
		row.remind_statuses = json.dumps(parse_statuses(row.remind_statuses))

	if not doc.is_new():
		kept = {row.name for row in doc.milestones if row.name}
		lost = [
			a.alert_name
			for a in frappe.get_all(ALERT, filters={"timeline": doc.name}, fields=["alert_name", "milestone"])
			if a.milestone not in kept
		]
		if lost:
			frappe.throw(
				f"You removed an activity that these alerts remind about: {', '.join(lost)}. "
				"Delete or re-link those alerts first."
			)


def check_timeline_not_in_use(name):
	alerts = frappe.get_all(ALERT, filters={"timeline": name}, pluck="alert_name")
	if alerts:
		frappe.throw(f"This timeline is used by alerts: {', '.join(alerts)}. Delete or re-link those alerts first.")


# ---------------------------------------------------------------------------
# Portal API
# ---------------------------------------------------------------------------


def timeline_rows():
	timelines = frappe.get_all(
		TIMELINE,
		fields=["name", "timeline_name", "ao_unit", "irb_cycle", "is_active", "notes", "modified"],
		order_by="is_active desc, modified desc",
	)
	if not timelines:
		return []
	names = [t.name for t in timelines]
	rows = frappe.get_all(
		MILESTONE,
		filters={"parenttype": TIMELINE, "parent": ("in", names)},
		fields=["name", "parent", "idx", "activity", "start_date", "end_date", "time_note", "remind_statuses"],
		order_by="idx asc",
	)
	units = {
		u.name: u
		for u in frappe.get_all(
			AOU, filters={"name": ("in", [t.ao_unit for t in timelines if t.ao_unit] or [""])}, fields=["name", "ao_name", "ao_type"]
		)
	}
	reminders = {}
	for a in frappe.get_all(ALERT, filters={"timeline": ("in", names)}, fields=["milestone", "enabled"]):
		reminders.setdefault(a.milestone, []).append(a.enabled)

	by_parent = {}
	for r in rows:
		r.remind_statuses = parse_statuses(r.remind_statuses)
		r.deadline = deadline_of(r)
		r.reminders = len(reminders.get(r.name, []))
		r.active_reminders = sum(1 for e in reminders.get(r.name, []) if cint(e))
		by_parent.setdefault(r.parent, []).append(r)
	for t in timelines:
		unit = units.get(t.ao_unit)
		t.unit_name = unit.ao_name if unit else None
		t.unit_type = unit.ao_type if unit else None
		t.milestones = by_parent.get(t.name, [])
	return timelines


def unit_options():
	"""Units a timeline can apply to, with their path, in tree order."""
	units = frappe.get_all(
		AOU, fields=["name", "ao_name", "ao_type", "parent_academic_organizational_unit as parent", "lft"], order_by="lft asc"
	)
	by_name = {u.name: u for u in units}
	for u in units:
		path, cur, guard = [], u, 0
		while cur and guard < 20:
			path.append(cur.ao_name or cur.name)
			cur = by_name.get(cur.parent)
			guard += 1
		u.path = " / ".join(reversed(path))
	return [{"name": u.name, "ao_name": u.ao_name, "ao_type": u.ao_type, "path": u.path} for u in units]


@frappe.whitelist()
def get_timelines():
	_require_admin()
	return timeline_rows()


def _parse(data):
	if isinstance(data, str):
		data = frappe.parse_json(data)
	return frappe._dict(data or {})


@frappe.whitelist(methods=["POST"])
def save_timeline(data):
	"""Create or update a timeline and its activities in one save."""
	_require_admin()
	data = _parse(data)
	doc = frappe.get_doc(TIMELINE, data.name) if data.name else frappe.new_doc(TIMELINE)
	doc.timeline_name = data.timeline_name
	doc.ao_unit = data.ao_unit or None
	doc.irb_cycle = data.irb_cycle or None
	doc.is_active = 1 if cint(data.is_active if data.is_active is not None else 1) else 0
	doc.notes = (data.notes or "").strip() or None

	# Keep the row name only for rows that already belong to this timeline:
	# alerts link to it, and Frappe would silently drop a row saved with an
	# unknown name (its UPDATE matches nothing).
	existing = {r.name for r in doc.milestones} if data.name else set()
	rows = []
	for r in data.milestones or []:
		r = frappe._dict(r)
		row = {
			"activity": r.activity,
			"start_date": r.start_date or None,
			"end_date": r.end_date or None,
			"time_note": r.time_note,
			"remind_statuses": json.dumps(parse_statuses(r.remind_statuses)),
		}
		if r.name and r.name in existing:
			row["name"] = r.name
		rows.append(row)
	doc.set("milestones", rows)
	doc.save()
	return doc.name


@frappe.whitelist(methods=["POST"])
def delete_timeline(name):
	_require_admin()
	if not frappe.db.exists(TIMELINE, name):
		frappe.throw("This timeline no longer exists.")
	frappe.delete_doc(TIMELINE, name)


# ---------------------------------------------------------------------------
# Paste from a document
# ---------------------------------------------------------------------------
# Schools publish their timeline as a Word/Excel table. Copying the table
# gives one line per row with tab-separated cells, e.g.
#   "Start reviewing IRB forms by mentor<TAB>25th July to 5th August"
# Dates come in many shapes: "29th June 2026", "16th September, 2026",
# "25th July to 5th August", "5th August-10th August", "10th-15th August",
# "2026-07-25", "25/07/2026" (day first). A missing year is taken from the
# other date in the cell, then from the rows above, then the current year.

MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
MAX_PASTE_LINES = 200

_ORDINAL = re.compile(r"\b(\d{1,2})(st|nd|rd|th)\b", re.I)
_DAY_RANGE = re.compile(r"\b(\d{1,2})\s*(?:-|–|—|to|till|until)\s*(\d{1,2})\s+([a-z]{3,9})\.?(?:\s+(\d{4}))?\b", re.I)
_DAY_MONTH = re.compile(r"\b(\d{1,2})\s*([a-z]{3,9})\.?(?:\s+(\d{4}))?\b", re.I)
_MONTH_DAY = re.compile(r"\b([a-z]{3,9})\.?\s+(\d{1,2})(?:\s+(\d{4}))?\b", re.I)
_JOINERS = {"to", "till", "until", "and", "-", "–", "—", "from"}
_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_NUMERIC = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\b")


def _month(word):
	return MONTHS.get((word or "")[:3].lower()) if word and word[:3].lower() in MONTHS and word.isalpha() else None


def _find_dates(cell):
	"""[(day, month, year|None, start, end)] in the order they appear."""
	# Case is kept so the rest of the cell can become the note ("6:00 PM").
	text = re.sub(r"\s+", " ", _ORDINAL.sub(r"\1", cell or "").replace(",", " "))
	found = []

	def add(d, m, y, span):
		if m and 1 <= int(d) <= 31 and not any(s < span[1] and span[0] < e for *_, s, e in found):
			found.append((int(d), m, int(y) if y else None, span[0], span[1]))

	for g in _ISO.finditer(text):
		add(g.group(3), int(g.group(2)) if 1 <= int(g.group(2)) <= 12 else None, g.group(1), g.span())
	for g in _NUMERIC.finditer(text):
		y = g.group(3)
		y = f"20{y}" if len(y) == 2 else y
		add(g.group(1), int(g.group(2)) if 1 <= int(g.group(2)) <= 12 else None, y, g.span())
	for g in _DAY_RANGE.finditer(text):  # "10-15 august": the month belongs to both days
		m = _month(g.group(3))
		if m:
			add(g.group(1), m, g.group(4), (g.start(1), g.end(1)))
			add(g.group(2), m, g.group(4), (g.start(2), g.end()))
	for g in _DAY_MONTH.finditer(text):
		add(g.group(1), _month(g.group(2)), g.group(3), g.span())
	for g in _MONTH_DAY.finditer(text):
		add(g.group(2), _month(g.group(1)), g.group(3), g.span())
	return sorted(found, key=lambda f: f[3]), text


def _leftover(text, found):
	"""Text in the date cell that isn't a date, e.g. "6:00 PM" in "3 Oct 2026 6:00 PM"."""
	out, pos = [], 0
	for *_, start, end in found:
		out.append(text[pos:start])
		pos = end
	out.append(text[pos:])
	words = [w for w in " ".join(out).split() if w.lower().strip(".,;:()") not in _JOINERS]
	rest = " ".join(words).strip(" -–—,;:")
	return rest if re.search(r"[A-Za-z0-9]", rest) else ""


def _real_date(d, m, y):
	import datetime

	try:
		return datetime.date(y, m, d)
	except ValueError:
		return None


def _split_cells(line):
	if "\t" in line:
		return [c.strip() for c in line.split("\t")]
	# No tabs (pasted from a PDF or plain text): cut where the first real
	# date starts — not at the first digit ("within 5 days" isn't a date).
	found, norm = _find_dates(line)
	if not found:
		return [line.strip()]
	cut = found[0][3]
	return [norm[:cut].strip(" -–:"), norm[cut:].strip()]


_HEADER_WORDS = {"activity", "activities", "task", "tasks", "event", "events", "milestone", "milestones", "date", "dates",
	"date(s)", "time", "timing", "remarks", "notes", "note", "deadline", "deadlines", "s.no", "sl", "no", "no.", "#", "details"}
_TITLE = re.compile(r"^(deadlines?|timeline|irb timeline|schedule|irb calendar)\b", re.I)
_DATE_WORDS = {"to", "till", "until", "and", "from", "-", "–", "—"}


def _is_header(line):
	words = [w.strip(":()").lower() for w in line.replace("\t", " ").split()]
	return bool(words) and all(w in _HEADER_WORDS for w in words)


def _is_date_fragment(line):
	"""The tail of a wrapped date cell, e.g. "August" or "5th August 2026"."""
	words = _ORDINAL.sub(r"\1", line).replace(",", " ").split()
	return bool(words) and all(w.isdigit() or _month(w.strip(".")) or w.lower() in _DATE_WORDS for w in words)


def _join_wrapped_lines(lines):
	"""Text copied without tabs (from a PDF, or Word's rendered view) puts
	each wrapped line of a cell on its own line: "Last date for submission
	of IRB forms by student to the" / "IRB Committee 25th July 2026". Join
	undated lines onto the next dated one, and a trailing date fragment
	("August") back onto the line above. Lines with tabs are whole table
	rows and are never joined. Returns (lines, title)."""
	out, pending, title = [], [], None
	for line in lines:
		tabbed = "\t" in line
		if _is_header(line):
			if pending and not out and title is None:
				title = " ".join(pending)  # "School of Development" above the header row
			pending = []
			continue
		if not tabbed and not out and not pending and title is None and _TITLE.match(line.strip()):
			title = line.strip()
			continue
		if not tabbed and out and not pending and _is_date_fragment(line) and not _find_dates(line)[0]:
			out[-1] = f"{out[-1]} {line.strip()}"
			continue
		if not tabbed and not _find_dates(line)[0]:
			pending.append(line.strip())
			continue
		if pending:
			line = " ".join(pending) + " " + line.lstrip()
			pending = []
		out.append(line)
	if pending:
		out.append(" ".join(pending))  # nothing dated after it: kept, flagged "No date found"
	return out, title


def parse_activities_text(text, default_year=None):
	"""Rows from a pasted table: {activity, start_date, end_date, time_note, problem}.
	Also returns a timeline name suggested by a heading such as
	"Deadlines for School of Development"."""
	default_year = int(default_year or getdate(nowdate()).year)
	lines = [ln for ln in (text or "").replace("\r", "").split("\n") if ln.strip()][:MAX_PASTE_LINES]
	lines, title = _join_wrapped_lines(lines)
	rows, carry_year = [], None
	for line in lines:
		cells = [c for c in _split_cells(line) if c != ""]
		if not cells:
			continue
		activity = " ".join(cells[0].split())
		rest = cells[1:]
		date_idx = next((i for i, c in enumerate(rest) if _find_dates(c)[0]), None)
		if date_idx is None:
			rows.append({"activity": activity, "start_date": None, "end_date": None,
				"time_note": " ".join(" ".join(rest).split()) or None, "problem": "No date found"})
			continue

		found, normalized = _find_dates(rest[date_idx])
		notes = [_leftover(normalized, found[:2])] + [c for i, c in enumerate(rest) if i != date_idx]
		note = " ".join(" ".join(n for n in notes if n).split()) or None
		years = [f[2] for f in found if f[2]]
		cell_year = years[-1] if years else None
		dates, problem = [], None
		for d, m, y, *_ in found[:2]:
			dt = _real_date(d, m, y or cell_year or carry_year or default_year)
			if not dt:
				problem = "The date doesn't exist"
				break
			dates.append(dt)
		start = dates[0] if dates else None
		end = dates[1] if len(dates) > 1 else None
		if start and end and end < start:
			if not found[0][2]:  # "20 Dec to 5 Jan": the start is in the previous year
				start = _real_date(start.day, start.month, start.year - 1)
			if not start or end < start:
				problem, end = "The end date is before the start date", None
		if end == start:
			end = None
		if start:
			carry_year = (end or start).year
		rows.append({"activity": activity or "(no activity name)", "start_date": str(start) if start else None,
			"end_date": str(end) if end else None, "time_note": note, "problem": problem})
	if title:
		title = re.sub(r"^(deadlines?|timeline|irb timeline|schedule|irb calendar)\s+(for|of)\s+", "", title, flags=re.I).strip() or None
	return {"rows": rows, "title": title}


@frappe.whitelist(methods=["POST"])
def parse_activities(text=None):
	_require_admin()
	if len(text or "") > 50_000:
		frappe.throw("That's too much text to read at once. Paste one timeline table at a time.")
	return parse_activities_text(text)
