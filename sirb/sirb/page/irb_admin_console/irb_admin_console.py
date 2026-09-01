# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt

import json

import frappe

# Canonical status list — must match the "status" Select field options on
# IRB Project exactly. This is the single source of truth for workflow
# stage; the dashboard never invents or duplicates status values.
STATUS_LIST = [
	"Awaiting proposal completion by student",
	"Awaiting Faculty mentor approval",
	"Awaiting student correction for mentor feedback",
	"Awaiting primary reviewer comments to secondary reviewer",
	"Awaiting secondary reviewer comments to primary reviewer",
	"Awaiting reviewer feedback to student",
	"Awaiting student correction for reviewer feedback",
	"Provisionally approved",
	"Awaiting final approval",
	"Approved",
]

# Short keys used as dashboard/table column ids, mapped to the real status string.
STATUS_KEY_MAP = {
	"student_action": "Awaiting proposal completion by student",
	"mentor_approval": "Awaiting Faculty mentor approval",
	"mentor_correction": "Awaiting student correction for mentor feedback",
	"primary_reviewer": "Awaiting primary reviewer comments to secondary reviewer",
	"secondary_reviewer": "Awaiting secondary reviewer comments to primary reviewer",
	"reviewer_feedback": "Awaiting reviewer feedback to student",
	"reviewer_correction": "Awaiting student correction for reviewer feedback",
	"provisional": "Provisionally approved",
	"final_approval": "Awaiting final approval",
	"approved": "Approved",
}
KEY_BY_STATUS = {v: k for k, v in STATUS_KEY_MAP.items()}

# Grouping of granular statuses into the higher-level "who needs to act"
# buckets used by the summary cards and the Pending Actions section.
PENDING_ACTION_GROUPS = {
	"student_action_required": [
		"Awaiting proposal completion by student",
		"Awaiting student correction for mentor feedback",
		"Awaiting student correction for reviewer feedback",
	],
	"mentor_action_required": ["Awaiting Faculty mentor approval"],
	"reviewer_action_required": [
		"Awaiting primary reviewer comments to secondary reviewer",
		"Awaiting secondary reviewer comments to primary reviewer",
		"Awaiting reviewer feedback to student",
	],
	"final_approval_required": ["Awaiting final approval"],
}

# Statuses that represent "pending" work for each named role, used for the
# per-person mentor/reviewer workload cards.
MENTOR_PENDING_STATUSES = ["Awaiting Faculty mentor approval"]
PRIMARY_REVIEWER_PENDING_STATUSES = [
	"Awaiting primary reviewer comments to secondary reviewer",
	"Awaiting reviewer feedback to student",
]
SECONDARY_REVIEWER_PENDING_STATUSES = ["Awaiting secondary reviewer comments to primary reviewer"]

ALLOWED_ROLES = {"System Manager", "Administrator"}


def _check_permission():
	if not (set(frappe.get_roles()) & ALLOWED_ROLES):
		frappe.throw(
			"You do not have permission to view this dashboard.",
			frappe.PermissionError,
		)


def _build_filters_clause(filters):
	"""Build a parametrised SQL WHERE clause from dashboard filters.

	Returns (clause, params) where clause is a string starting with " and ..."
	(or empty) and params is a dict for frappe.db.sql placeholders.
	"""
	filters = filters or {}
	clauses = []
	params = {}

	def add_multi(key, column):
		"""Accepts a scalar or a list for `key` (multiselect filters send a
		list of values) and appends an `=` or `in (...)` clause accordingly.
		"""
		value = filters.get(key)
		if not value:
			return
		if isinstance(value, (list, tuple)):
			value = [v for v in value if v]
			if not value:
				return
			placeholders = []
			for i, v in enumerate(value):
				pkey = f"{key}_{i}"
				params[pkey] = v
				placeholders.append(f"%({pkey})s")
			clauses.append(f"{column} in ({','.join(placeholders)})")
		else:
			params[key] = value
			clauses.append(f"{column} = %({key})s")

	add_multi("irb_unit", "p.irb_unit")
	add_multi("academic_year", "s.academic_year")
	add_multi("irb_cycle", "p.irb_cycle")
	add_multi("faculty_mentor", "p.faculty_mentor")
	add_multi("primary_reviewer", "p.primary_reviewer")
	add_multi("secondary_reviewer", "p.secondary_reviewer")

	if filters.get("status"):
		clauses.append("p.status = %(status)s")
		params["status"] = filters["status"]

	if filters.get("from_date"):
		clauses.append("p.modified >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		clauses.append("p.modified <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	clause = ""
	if clauses:
		clause = " and " + " and ".join(clauses)
	return clause, params


BASE_JOIN = """
	from `tabStudent Project Mapping` as sp
	join `tabIRB Project` as p on sp.irb_project = p.name
	join `tabStudent` as s on sp.student = s.name
	join `tabIRB Unit` as iu on p.irb_unit = iu.name
	where sp.status = "active"
"""


@frappe.whitelist()
def get_dashboard_data(filters=None):
	"""Single aggregated payload for the whole dashboard: summary cards,
	programme matrix, pending action buckets and chart data. Everything is
	computed server-side via grouped SQL — no per-record data is sent to
	the browser here.
	"""
	_check_permission()
	if isinstance(filters, str):
		filters = json.loads(filters) if filters else {}
	where_extra, params = _build_filters_clause(filters)

	# ---- Programme x status matrix -------------------------------------------------
	rows = frappe.db.sql(
		f"""
		select iu.name as irb_unit, iu.ao_name as programme, p.status as status,
			count(*) as cnt
		{BASE_JOIN}{where_extra}
		group by iu.name, p.status
		""",
		params,
		as_dict=True,
	)

	programme_matrix = {}
	for r in rows:
		key = r["irb_unit"]
		if key not in programme_matrix:
			programme_matrix[key] = {
				"irb_unit": r["irb_unit"],
				"programme": r["programme"],
				"total": 0,
				"statuses": {k: 0 for k in STATUS_KEY_MAP},
			}
		status_key = KEY_BY_STATUS.get(r["status"])
		if status_key:
			programme_matrix[key]["statuses"][status_key] = r["cnt"]
		programme_matrix[key]["total"] += r["cnt"]

	programme_matrix = sorted(programme_matrix.values(), key=lambda x: x["programme"] or "")

	# ---- Overall status counts (for cards + chart) ----------------------------------
	status_counts = {k: 0 for k in STATUS_KEY_MAP}
	total_students = 0
	for r in rows:
		status_key = KEY_BY_STATUS.get(r["status"])
		if status_key:
			status_counts[status_key] += r["cnt"]
		total_students += r["cnt"]

	# ---- Pending action groups -------------------------------------------------------
	pending_actions = {}
	for group_key, statuses in PENDING_ACTION_GROUPS.items():
		pending_actions[group_key] = sum(
			status_counts[KEY_BY_STATUS[s]] for s in statuses if KEY_BY_STATUS.get(s)
		)

	return {
		"total_students": total_students,
		"status_counts": status_counts,
		"pending_actions": pending_actions,
		"programme_matrix": programme_matrix,
		"status_list": STATUS_LIST,
		"status_key_map": STATUS_KEY_MAP,
	}


@frappe.whitelist()
def get_filter_options():
	"""Options for the filter bar — programmes, academic years, cycles,
	mentors and reviewers actually present in the data (not hard-coded).
	"""
	_check_permission()

	programmes = frappe.db.sql(
		"""select distinct iu.name, iu.ao_name
		from `tabIRB Unit` as iu
		join `tabIRB Project` as p on p.irb_unit = iu.name
		order by iu.ao_name""",
		as_dict=True,
	)

	academic_years = frappe.db.sql(
		"""select distinct academic_year from `tabStudent`
		where academic_year is not null and academic_year != ''
		order by academic_year desc""",
		as_dict=True,
	)

	cycles = frappe.db.sql(
		"""select distinct irb_cycle from `tabIRB Project`
		where irb_cycle is not null and irb_cycle != ''
		order by irb_cycle desc""",
		as_dict=True,
	)

	mentors = frappe.db.sql(
		"""select distinct f.name, f.full_name
		from `tabFaculty` as f
		join `tabIRB Project` as p on p.faculty_mentor = f.name
		order by f.full_name""",
		as_dict=True,
	)

	reviewers = frappe.db.sql(
		"""select distinct f.name, f.full_name from `tabFaculty` as f
		where f.name in (
			select primary_reviewer from `tabIRB Project` where primary_reviewer is not null
			union
			select secondary_reviewer from `tabIRB Project` where secondary_reviewer is not null
		)
		order by f.full_name""",
		as_dict=True,
	)

	return {
		"programmes": programmes,
		"academic_years": [d["academic_year"] for d in academic_years],
		"cycles": [d["irb_cycle"] for d in cycles],
		"mentors": mentors,
		"reviewers": reviewers,
		"statuses": STATUS_LIST,
	}


@frappe.whitelist()
def get_role_workload(filters=None):
	"""Per-person pending workload for Faculty Mentors, Primary Reviewers and
	Secondary Reviewers, restricted to people who actually have at least one
	pending project in that role (so the list stays short and actionable).
	"""
	_check_permission()
	if isinstance(filters, str):
		filters = json.loads(filters) if filters else {}
	where_extra, params = _build_filters_clause(filters)

	def _workload(role_field, pending_statuses, role_key):
		placeholders = []
		local_params = dict(params)
		for i, st in enumerate(pending_statuses):
			pkey = f"{role_key}_status_{i}"
			local_params[pkey] = st
			placeholders.append(f"%({pkey})s")

		rows = frappe.db.sql(
			f"""
			select f.name as faculty_id, f.full_name as faculty_name, count(*) as pending_count
			from `tabStudent Project Mapping` as sp
			join `tabIRB Project` as p on sp.irb_project = p.name
			join `tabStudent` as s on sp.student = s.name
			join `tabIRB Unit` as iu on p.irb_unit = iu.name
			join `tabFaculty` as f on p.{role_field} = f.name
			where sp.status = "active"
			and p.status in ({','.join(placeholders)})
			{where_extra}
			group by f.name
			order by pending_count desc
			""",
			local_params,
			as_dict=True,
		)
		return rows

	return {
		"mentors": _workload("faculty_mentor", MENTOR_PENDING_STATUSES, "mentor"),
		"primary_reviewers": _workload("primary_reviewer", PRIMARY_REVIEWER_PENDING_STATUSES, "pr"),
		"secondary_reviewers": _workload("secondary_reviewer", SECONDARY_REVIEWER_PENDING_STATUSES, "sr"),
	}


@frappe.whitelist()
def get_drilldown_students(filters=None, status=None, irb_unit=None, pending_group=None, role_person=None):
	"""Row-level drill-down for the modal table. Accepts an explicit status,
	an irb_unit, a pending_group key (mapped to its underlying statuses), or
	a role_person filter (mentor/primary_reviewer/secondary_reviewer + Faculty
	id, mapped to that role's pending statuses) — combined with the active
	dashboard filters. With none of these, returns every active student.
	"""
	_check_permission()
	if isinstance(filters, str):
		filters = json.loads(filters) if filters else {}
	if isinstance(role_person, str) and role_person.startswith("{"):
		role_person = json.loads(role_person)
	filters = dict(filters or {})

	if irb_unit:
		filters["irb_unit"] = irb_unit
	if status:
		filters["status"] = status

	where_extra, params = _build_filters_clause(filters)

	extra_clause = ""
	if pending_group and pending_group in PENDING_ACTION_GROUPS:
		statuses = PENDING_ACTION_GROUPS[pending_group]
		placeholders = []
		for i, st in enumerate(statuses):
			pkey = f"pg_status_{i}"
			params[pkey] = st
			placeholders.append(f"%({pkey})s")
		extra_clause = f" and p.status in ({','.join(placeholders)})"
	elif role_person and role_person.get("role") and role_person.get("faculty"):
		role_field_map = {
			"mentor": ("faculty_mentor", MENTOR_PENDING_STATUSES),
			"primary_reviewer": ("primary_reviewer", PRIMARY_REVIEWER_PENDING_STATUSES),
			"secondary_reviewer": ("secondary_reviewer", SECONDARY_REVIEWER_PENDING_STATUSES),
		}
		mapping = role_field_map.get(role_person["role"])
		if mapping:
			field, statuses = mapping
			placeholders = []
			for i, st in enumerate(statuses):
				pkey = f"role_status_{i}"
				params[pkey] = st
				placeholders.append(f"%({pkey})s")
			params["role_person_id"] = role_person["faculty"]
			extra_clause = f" and p.{field} = %(role_person_id)s and p.status in ({','.join(placeholders)})"

	rows = frappe.db.sql(
		f"""
		select
			s.name as student_id,
			s.full_name as student_name,
			iu.ao_name as programme,
			p.name as project_id,
			p.title as project_title,
			p.status as status,
			fm.full_name as faculty_mentor,
			pr.full_name as primary_reviewer,
			sr.full_name as secondary_reviewer,
			p.modified as last_updated
		from `tabStudent Project Mapping` as sp
		join `tabIRB Project` as p on sp.irb_project = p.name
		join `tabStudent` as s on sp.student = s.name
		join `tabIRB Unit` as iu on p.irb_unit = iu.name
		left join `tabFaculty` as fm on p.faculty_mentor = fm.name
		left join `tabFaculty` as pr on p.primary_reviewer = pr.name
		left join `tabFaculty` as sr on p.secondary_reviewer = sr.name
		where sp.status = "active"
		{where_extra}{extra_clause}
		order by p.modified desc
		limit 1000
		""",
		params,
		as_dict=True,
	)

	return rows


@frappe.whitelist()
def get_recent_activity(filters=None, limit=25):
	"""Recent workflow activity derived from the Version log on IRB Project.
	Each Version stores a JSON diff of changed fields; we scan for changes
	to the `status` field, which is the system's single point of workflow
	transition (see IRBProject.on_change).
	"""
	_check_permission()
	if isinstance(filters, str):
		filters = json.loads(filters) if filters else {}
	limit = int(limit or 25)

	where_extra, params = _build_filters_clause(filters)

	# Restrict candidate projects using the same filters as the rest of the
	# dashboard, then scan their recent versions for status changes.
	project_names = frappe.db.sql(
		f"""
		select distinct p.name
		{BASE_JOIN}{where_extra}
		""",
		params,
		as_dict=True,
	)
	if not project_names:
		return []
	names = [d["name"] for d in project_names]

	versions = frappe.db.sql(
		"""
		select v.name, v.ref_doctype, v.docname, v.data, v.owner, v.creation
		from `tabVersion` as v
		where v.ref_doctype = "IRB Project" and v.docname in %(names)s
		order by v.creation desc
		limit 500
		""",
		{"names": names},
		as_dict=True,
	)

	activity = []
	for v in versions:
		try:
			data = frappe.parse_json(v["data"])
		except Exception:
			continue
		changed = data.get("changed") or []
		for change in changed:
			if len(change) >= 3 and change[0] == "status":
				activity.append(
					{
						"project_id": v["docname"],
						"from_status": change[1],
						"to_status": change[2],
						"performed_by": v["owner"],
						"date": v["creation"],
					}
				)

	if not activity:
		return []

	# Enrich with project/student/programme context for display.
	proj_names = list({a["project_id"] for a in activity})
	details = frappe.db.sql(
		f"""
		select p.name as project_id, p.title as project_title, iu.ao_name as programme,
			group_concat(s.full_name separator ', ') as student_names
		from `tabIRB Project` as p
		join `tabIRB Unit` as iu on p.irb_unit = iu.name
		left join `tabStudent Project Mapping` as sp on sp.irb_project = p.name and sp.status = "active"
		left join `tabStudent` as s on sp.student = s.name
		where p.name in %(names)s
		group by p.name
		""",
		{"names": proj_names},
		as_dict=True,
	)
	detail_map = {d["project_id"]: d for d in details}

	for a in activity:
		d = detail_map.get(a["project_id"], {})
		a["project_title"] = d.get("project_title")
		a["programme"] = d.get("programme")
		a["student_names"] = d.get("student_names")

	activity.sort(key=lambda a: a["date"], reverse=True)
	return activity[:limit]
