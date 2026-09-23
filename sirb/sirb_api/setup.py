# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Whitelisted CRUD for the portal's Setup page: the Academic
Organizational Unit tree and IRB Units (review settings + committee;
committee members' Faculty <-> Academic Organizational Unit memberships
are resolved or created on save).

Every method is restricted to System Manager (the same role the three
DocTypes grant write access to), and every write still goes through
Document.insert()/save()/delete_doc(), so the DocType controllers
(NestedSet tree maintenance, IRBUnit.on_update's reviewer role sync,
FacultyAcademicOrganizationalUnit.validate's title) run exactly as they
do from Desk. Validation errors are raised as plain-text messages the
Vue frontend can show verbatim.
"""

import frappe
from frappe.utils import cint, strip_html

AOU = "Academic Organizational Unit"
IRB_UNIT = "IRB Unit"
FAOU = "Faculty Academic Organizational Unit"

AO_TYPES = ("University", "Campus", "School", "Department", "Programme")
REVIEWER_COUNTS = ("1", "2")


def _require_admin():
	frappe.only_for("System Manager")


def _parse(data):
	if isinstance(data, str):
		data = frappe.parse_json(data)
	return frappe._dict(data or {})


def _clean(value):
	return (value or "").strip()


def _friendly_delete(doctype, name, label):
	"""delete_doc() raises LinkExistsError / NestedSetChildExistsError with
	HTML-laden messages already queued in message_log — replace them with
	one plain sentence so the toast in the frontend stays readable."""
	try:
		frappe.delete_doc(doctype, name)
	except frappe.LinkExistsError:
		frappe.clear_messages()
		frappe.throw(f"{label} is still in use by other records (projects, units or memberships) and cannot be deleted.")
	except frappe.ValidationError as e:
		frappe.clear_messages()
		frappe.throw(strip_html(str(e)) or f"{label} could not be deleted.")


@frappe.whitelist()
def get_setup_data():
	"""Everything the Setup page renders, in one round trip."""
	_require_admin()

	units = frappe.get_all(
		AOU,
		fields=["name", "ao_name", "ao_type", "ao_code", "is_group", "parent_academic_organizational_unit as parent", "lft"],
		order_by="lft asc",
	)

	memberships = frappe.db.sql(
		f"""
		select faou.name, faou.faculty_member, faou.ao_unit, ifnull(nullif(faou.status, ''), 'active') as status,
			f.full_name as faculty_name, u.email as faculty_email, aou.ao_name as unit_name
		from `tab{FAOU}` as faou
		left join tabFaculty as f on f.name = faou.faculty_member
		left join tabUser as u on u.name = f.system_user
		left join `tab{AOU}` as aou on aou.name = faou.ao_unit
		order by f.full_name asc, aou.ao_name asc
		""",
		as_dict=True,
	)

	irb_units = frappe.get_all(
		IRB_UNIT,
		fields=["name", "ao_unit", "ao_name", "mentor_required", "num_reviewers", "modified"],
		order_by="ao_name asc",
	)
	committee_rows = frappe.get_all(
		"IRB Faculty Grouping",
		filters={"parenttype": IRB_UNIT},
		fields=["parent", "faculty_member"],
		order_by="idx asc",
	)
	project_counts = dict(
		frappe.db.sql("select irb_unit, count(*) from `tabIRB Project` where ifnull(irb_unit, '') != '' group by irb_unit")
	)
	committee_by_unit = {}
	for row in committee_rows:
		committee_by_unit.setdefault(row.parent, []).append(row.faculty_member)
	for unit in irb_units:
		unit.members = committee_by_unit.get(unit.name, [])
		unit.num_reviewers = unit.num_reviewers or "1"
		unit.project_count = project_counts.get(unit.name, 0)

	faculty = frappe.get_all("Faculty", fields=["name", "full_name", "system_user"], order_by="full_name asc")

	return {
		"units": units,
		"irb_units": irb_units,
		"memberships": memberships,
		"faculty": faculty,
		"ao_types": list(AO_TYPES),
	}


# ---------------------------------------------------------------------------
# Academic Organizational Unit
# ---------------------------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def save_org_unit(data):
	"""Create a unit, or edit an existing one's name/type/group flag.

	The document name is derived from `<parent>-<code>` in
	AcademicOrganizationalUnit.autoname(), so code and parent are fixed
	after creation — changing them would silently desync the name every
	other record links to.
	"""
	_require_admin()
	data = _parse(data)

	ao_name = _clean(data.ao_name)
	ao_type = _clean(data.ao_type)
	is_group = 1 if cint(data.is_group) else 0

	if not ao_name:
		frappe.throw("Unit name is required.")
	if ao_type not in AO_TYPES:
		frappe.throw(f"Unit type must be one of: {', '.join(AO_TYPES)}.")

	duplicate = frappe.db.get_value(AOU, {"ao_name": ao_name, "name": ("!=", data.name or "")})
	if duplicate:
		frappe.throw(f"Another unit is already named '{ao_name}'.")

	if data.name:
		doc = frappe.get_doc(AOU, data.name)
		if not is_group and doc.is_group and frappe.db.exists(AOU, {"parent_academic_organizational_unit": doc.name}):
			frappe.throw("This unit has child units, so it must stay a group. Move or delete its children first.")
		doc.ao_name = ao_name
		doc.ao_type = ao_type
		doc.is_group = is_group
		doc.save()
		return doc.name

	ao_code = _clean(data.ao_code)
	parent = _clean(data.parent)
	if not ao_code:
		frappe.throw("Unit code is required.")
	if any(ch in ao_code for ch in "/%#?"):
		frappe.throw("Unit code cannot contain / % # or ?.")

	if parent:
		if not frappe.db.exists(AOU, parent):
			frappe.throw(f"Parent unit '{parent}' does not exist.")
		if not frappe.db.get_value(AOU, parent, "is_group"):
			frappe.throw("The selected parent is not a group. Mark it as a group before adding units under it.")
	elif not cint(data.allow_root) and frappe.db.sql(
		f"select 1 from `tab{AOU}` where ifnull(parent_academic_organizational_unit, '') = '' limit 1"
	):
		# A second top-level node is almost always an accident, so once a
		# root exists the caller has to ask for another one explicitly.
		frappe.throw("Select a parent unit.")

	expected_name = f"{parent}-{ao_code}" if parent else ao_code
	if frappe.db.exists(AOU, expected_name):
		frappe.throw(f"A unit with code '{ao_code}' already exists under this parent.")

	doc = frappe.get_doc(
		{
			"doctype": AOU,
			"ao_name": ao_name,
			"ao_type": ao_type,
			"ao_code": ao_code,
			"is_group": is_group,
			"parent_academic_organizational_unit": parent or None,
		}
	)
	doc.insert()
	return doc.name


@frappe.whitelist(methods=["POST"])
def delete_org_unit(name):
	_require_admin()
	label = frappe.db.get_value(AOU, name, "ao_name")
	if not label:
		frappe.throw("This unit no longer exists.")
	if frappe.db.exists(AOU, {"parent_academic_organizational_unit": name}):
		frappe.throw(f"'{label}' has child units. Delete or move them first.")
	_friendly_delete(AOU, name, f"'{label}'")


# ---------------------------------------------------------------------------
# IRB Unit
# ---------------------------------------------------------------------------


def _resolve_committee(members, ao_unit):
	"""Turn the committee picked in the form into Faculty Academic
	Organizational Unit names (what IRB Faculty Grouping links to).

	Each entry is {"faculty": <Faculty name>, "membership": <FAOU name or
	None>}. An existing membership is kept as-is (it may belong to a
	sub-unit); otherwise the faculty's membership of this unit is reused,
	or created — so admins pick people, not membership records, just like
	the single IRB Unit form in Desk.
	"""
	resolved, seen_faculty = [], set()
	for entry in members or []:
		if isinstance(entry, str):
			entry = {"membership": entry}
		entry = frappe._dict(entry)
		membership = _clean(entry.membership)
		faculty = _clean(str(entry.faculty or ""))

		if membership:
			faculty_of_row = frappe.db.get_value(FAOU, membership, "faculty_member")
			if faculty_of_row is None:
				frappe.throw("A selected committee member no longer exists. Reload the page and try again.")
			faculty = str(faculty_of_row)
		elif not faculty or not frappe.db.exists("Faculty", faculty):
			frappe.throw("A selected faculty member no longer exists. Reload the page and try again.")

		if faculty in seen_faculty:
			name = frappe.db.get_value("Faculty", faculty, "full_name") or faculty
			frappe.throw(f"{name} is listed more than once in the committee.")
		seen_faculty.add(faculty)

		if not frappe.db.get_value("Faculty", faculty, "system_user"):
			# IRBUnit.update_reviewer_roles() dereferences Faculty.system_user
			# for every member and would otherwise crash half-way through.
			name = frappe.db.get_value("Faculty", faculty, "full_name") or faculty
			frappe.throw(f"{name} has no linked user account, so they can't be on an IRB committee.")

		if not membership:
			membership = frappe.db.get_value(FAOU, {"faculty_member": faculty, "ao_unit": ao_unit})
		if not membership:
			faou = frappe.get_doc({"doctype": FAOU, "faculty_member": faculty, "ao_unit": ao_unit, "status": "active"})
			faou.insert()
			membership = faou.name
		resolved.append(membership)
	return resolved


@frappe.whitelist(methods=["POST"])
def save_irb_unit(data):
	"""Create or update an IRB Unit and its committee in one save, so
	IRBUnit.on_update's reviewer-role sync runs once on the final state.
	Any membership created for a new committee member is part of the same
	request transaction, so a failed save leaves nothing behind."""
	_require_admin()
	data = _parse(data)

	ao_unit = _clean(data.ao_unit)
	num_reviewers = str(data.num_reviewers or "1")

	if not ao_unit or not frappe.db.exists(AOU, ao_unit):
		frappe.throw("Select a valid Academic Organizational Unit.")
	if num_reviewers not in REVIEWER_COUNTS:
		frappe.throw("Number of IRB Reviewers must be 1 or 2.")

	existing = frappe.db.get_value(IRB_UNIT, {"ao_unit": ao_unit, "name": ("!=", data.name or "")})
	if existing:
		unit_name = frappe.db.get_value(AOU, ao_unit, "ao_name")
		frappe.throw(f"'{unit_name}' already has an IRB Unit. Edit that one instead.")

	if data.name:
		doc = frappe.get_doc(IRB_UNIT, data.name)
		if doc.ao_unit != ao_unit and frappe.db.exists("IRB Project", {"irb_unit": doc.name}):
			frappe.throw("This IRB Unit already has projects, so its Academic Organizational Unit cannot be changed.")
	else:
		doc = frappe.new_doc(IRB_UNIT)

	members = _resolve_committee(data.members, ao_unit)

	doc.ao_unit = ao_unit
	doc.mentor_required = 1 if cint(data.mentor_required) else 0
	doc.num_reviewers = num_reviewers
	doc.set("irb_committee_faculty_members", [{"faculty_member": m} for m in members])
	doc.save()
	return doc.name


@frappe.whitelist(methods=["POST"])
def delete_irb_unit(name):
	_require_admin()
	label = frappe.db.get_value(IRB_UNIT, name, "ao_name")
	if label is None and not frappe.db.exists(IRB_UNIT, name):
		frappe.throw("This IRB Unit no longer exists.")
	if frappe.db.exists("IRB Project", {"irb_unit": name}):
		frappe.throw(f"The IRB Unit for '{label}' has projects and cannot be deleted.")
	_friendly_delete(IRB_UNIT, name, f"The IRB Unit for '{label}'")
	# Deleting the unit drops its committee, so re-run the same revoke
	# pass IRBUnit.on_update uses to strip now-orphaned reviewer roles.
	frappe.get_doc({"doctype": IRB_UNIT}).revoke_roles_if_not_needed()
