"""Dummy users for manually testing each SIRB role. Dev/test sites only.

Run (idempotent, safe to re-run):
	bench --site sirb.local execute sirb.test_users.create
Remove:
	bench --site sirb.local execute sirb.test_users.remove
"""

import frappe

PASSWORD = "Test@12345"
TEST_AO_UNIT = "Test"

# email, full name, roles, linked person doctype
TEST_USERS = [
	("sirb.admin@example.com", "Test Admin", ["System Manager"], None),
	("sirb.anchor@example.com", "Test Anchor", ["Faculty Member", "Anchor"], "Faculty"),
	("sirb.student@example.com", "Test Student", ["Student"], "Student"),
	# Teammates for the group projects below.
	("sirb.student2@example.com", "Test Student Two", ["Student"], "Student"),
	("sirb.student3@example.com", "Test Student Three", ["Student"], "Student"),
	("sirb.mentor@example.com", "Test Mentor", ["Faculty Member", "Faculty Mentor"], "Faculty"),
	(
		"sirb.primary@example.com",
		"Test Primary Reviewer",
		["Faculty Member", "IRB Reviewer", "Primary IRB Reviewer"],
		"Faculty",
	),
	(
		"sirb.secondary@example.com",
		"Test Secondary Reviewer",
		["Faculty Member", "IRB Reviewer", "Secondary IRB Reviewer"],
		"Faculty",
	),
]

# Reviewers are added to the Test IRB Unit committee so they can be auto-assigned.
COMMITTEE_USERS = ["sirb.primary@example.com", "sirb.secondary@example.com"]

PROJECT_PREFIX = "[TEST] "
# title, status, member emails, has primary reviewer
TEST_PROJECTS = [
	("Solo: Reading habits survey", "Awaiting proposal completion by student", ["sirb.student@example.com"], False),
	("Solo: Campus water audit", "Awaiting Faculty mentor approval", ["sirb.student@example.com"], False),
	(
		"Group: Street vendor livelihoods",
		"Awaiting reviewer feedback to student",
		["sirb.student@example.com", "sirb.student2@example.com", "sirb.student3@example.com"],
		True,
	),
	(
		"Group: Bird census of Sarjapur lake",
		"Approved",
		["sirb.student@example.com", "sirb.student2@example.com"],
		True,
	),
]


def create():
	frappe.flags.mute_emails = True
	for email, full_name, roles, person_doctype in TEST_USERS:
		user = _ensure_user(email, full_name, roles)
		if person_doctype:
			_ensure_person(person_doctype, user.name, full_name)
	_ensure_committee_members()
	_ensure_projects()
	frappe.db.commit()
	for email, _, roles, _ in TEST_USERS:
		print(f"{email:32} {', '.join(roles)}")
	print(f"Password for all: {PASSWORD}")


def remove():
	emails = [u[0] for u in TEST_USERS]
	projects = frappe.get_all("IRB Project", filters={"title": ["like", PROJECT_PREFIX + "%"]}, pluck="name")
	if projects:
		frappe.db.delete("Student Project Mapping", {"irb_project": ["in", projects]})
		frappe.db.delete("IRB Project", {"name": ["in", projects]})
	faculty = frappe.get_all("Faculty", filters={"system_user": ["in", emails]}, pluck="name")
	aou = frappe.get_all(
		"Faculty Academic Organizational Unit", filters={"faculty_member": ["in", faculty]}, pluck="name"
	) if faculty else []
	if aou:
		frappe.db.delete("IRB Faculty Grouping", {"faculty_member": ["in", aou]})
	for name in aou:
		frappe.delete_doc("Faculty Academic Organizational Unit", name, force=True)
	for name in faculty:
		frappe.delete_doc("Faculty", name, force=True)
	for name in frappe.get_all("Student", filters={"system_user": ["in", emails]}, pluck="name"):
		frappe.delete_doc("Student", name, force=True)
	for email in emails:
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True)
	frappe.db.commit()
	print("Removed test users")


def _ensure_user(email, full_name, roles):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": full_name, "send_welcome_email": 0})
	user.enabled = 1
	user.new_password = PASSWORD
	user.flags.ignore_password_policy = True
	user.save(ignore_permissions=True)
	user.add_roles(*roles)
	return user


def _ensure_person(doctype, user, full_name):
	if frappe.db.exists(doctype, {"system_user": user}):
		return
	doc = frappe.new_doc(doctype)
	doc.update({"full_name": full_name, "system_user": user})
	if doctype == "Student":
		doc.student_id = full_name
	doc.insert(ignore_permissions=True)


def _ensure_projects():
	# db_insert() skips the controllers on purpose: IRB Project.on_change re-syncs
	# mentor/reviewer roles for every user on the site, and Student Project
	# Mapping.after_insert emails the students.
	irb_unit = frappe.db.get_value("IRB Unit", {"ao_unit": TEST_AO_UNIT})
	if not irb_unit:
		return
	mentor = frappe.db.get_value("Faculty", {"system_user": "sirb.mentor@example.com"})
	primary = frappe.db.get_value("Faculty", {"system_user": "sirb.primary@example.com"})
	for title, status, members, has_reviewer in TEST_PROJECTS:
		title = PROJECT_PREFIX + title
		if frappe.db.exists("IRB Project", {"title": title}):
			continue
		project = frappe.new_doc("IRB Project")
		project.update(
			{
				"title": title,
				"topic": title,
				"abstract": "Dummy project for manual testing.",
				"status": status,
				"irb_unit": irb_unit,
				"irb_cycle": "August 2026",
				"faculty_mentor": mentor,
				"primary_reviewer": primary if has_reviewer else None,
				"num_reviewers": "1",
				"project_domain": "Humans",
				"i_hereby_confirm_the_above": 1,
			}
		)
		project.set_user_and_timestamp()
		project.db_insert()
		for email in members:
			mapping = frappe.new_doc("Student Project Mapping")
			mapping.update(
				{
					"student": frappe.db.get_value("Student", {"system_user": email}),
					"irb_project": project.name,
					# Approved projects have their mappings deactivated (IRB Project.on_change).
					"status": "inactive" if status == "Approved" else "active",
				}
			)
			mapping.set_user_and_timestamp()
			mapping.db_insert()


def _ensure_committee_members():
	irb_unit = frappe.db.get_value("IRB Unit", {"ao_unit": TEST_AO_UNIT})
	if not irb_unit:
		return
	unit = frappe.get_doc("IRB Unit", irb_unit)
	existing = {row.faculty_member for row in unit.irb_committee_faculty_members}
	for email in COMMITTEE_USERS:
		faculty = frappe.db.get_value("Faculty", {"system_user": email})
		aou = frappe.db.get_value(
			"Faculty Academic Organizational Unit", {"faculty_member": faculty, "ao_unit": TEST_AO_UNIT}
		)
		if not aou:
			aou = frappe.get_doc(
				{
					"doctype": "Faculty Academic Organizational Unit",
					"faculty_member": faculty,
					"ao_unit": TEST_AO_UNIT,
					"status": "active",
				}
			).insert(ignore_permissions=True).name
		if aou not in existing:
			# Insert the child row directly: IRB Unit.save() runs on_update, which
			# strips "IRB Reviewer" from every faculty user not on a committee.
			row = unit.append("irb_committee_faculty_members", {"faculty_member": aou})
			row.db_insert()
