
import frappe

def get_logged_in_doc(role_name):
    user = frappe.session.user
    role_doc_mapping = {
        "Faculty Mentor" : "Faculty",
        "Faculty Member" : "Faculty",
        "Primary Reviewer" : "Faculty",
        "Secondary Reviewer" : "Faculty",
        "Faculty": "Faculty",
        "Anchor" : "Faculty",
        "Student" : "Student",
    }
    doc_name = role_doc_mapping.get(role_name, None)
    # print(doc_name)
    if doc_name:
        fentries = frappe.db.get_all(doc_name, filters = {
            "system_user": user
        })
        if fentries:
            doc = frappe.get_doc(doc_name, fentries[0]["name"])
            return doc
    return None

def get_reviewers(irb_unit, exclude_faculty_id = None):

    irb_unit_doc = frappe.get_doc("IRB Unit", irb_unit)
    num_reviewers = int(irb_unit_doc.num_reviewers)
    print("Num reviewers ", num_reviewers)
    
    all_reviewers = []
    project_count_for_primary_reviewers = {}
    project_count_for_secondary_reviewers = {}
    for irb_faculty in irb_unit_doc.irb_committee_faculty_members:
        fmember = frappe.get_doc("Faculty Academic Organizational Unit", irb_faculty.faculty_member)
        print("Appending ", fmember.faculty_member)
        all_reviewers.append(fmember.faculty_member)
        # Initialize project count to 0 for all reviewers
        project_count_for_primary_reviewers[fmember.faculty_member] = 0
        if num_reviewers == 2:
            project_count_for_secondary_reviewers[fmember.faculty_member] = 0
    
    primary_reviewer_data = frappe.db.sql(
        '''select p.primary_reviewer, count(*) as count from `tabIRB Project` as p where 
        p.primary_reviewer is not null and p.irb_unit = %(irb_unit)s and p.status != "Approved" 
        group by p.primary_reviewer;''', {"irb_unit": irb_unit}, as_dict=1
    )
    print(primary_reviewer_data)
    for d in primary_reviewer_data:
        # primary_reviewers_with_projects.add(d["primary_reviewer"])
        if d["primary_reviewer"] in project_count_for_primary_reviewers:
            project_count_for_primary_reviewers[d["primary_reviewer"]] += d["count"]

    min_count = 0
    min_pr = None
    print("Project count for primary reviewers - ", project_count_for_primary_reviewers)

    # frappe.log_error(
    #     title=f"project_count_for_primary_reviewers",
    #     message=str(project_count_for_primary_reviewers)
    # )
    for pr, prc in project_count_for_primary_reviewers.items():
        #frappe.log_error(title="Debug", message=f"{pr}, {exclude_faculty_id}")
        if exclude_faculty_id is not None and str(pr) == str(exclude_faculty_id) or pr == exclude_faculty_id:
            #frappe.log_error(title="Debug", message=f"Skipping {pr}")
            continue
        if min_pr is None or prc <= min_count:
            min_count = prc
            min_pr = pr
    print("Current primary mins are ", min_count, min_pr)

    if num_reviewers == 2:
        print("Checking secondary")
        query = '''select p.secondary_reviewer, count(*) as count from `tabIRB Project` as p where 
            p.secondary_reviewer is not null and p.irb_unit = %(irb_unit)s and p.status != "Approved" 
            group by p.secondary_reviewer;'''
        secondary_reviewer_data = frappe.db.sql(
            query, {"irb_unit": irb_unit}, as_dict=1
        )
        for d in secondary_reviewer_data:
            # frappe.log_error(
            #     title=f"d",
            #     message=str(d)
            # )
            # secondary_reviewers_with_projects.add(d["secondary_reviewer"])
            if d["secondary_reviewer"] in project_count_for_secondary_reviewers:
                project_count_for_secondary_reviewers[d["secondary_reviewer"]] += d["count"]
        min_count = 0
        min_sr = None
        for sr, src in project_count_for_secondary_reviewers.items():
            print(sr, src)
            if sr == min_pr or (exclude_faculty_id is not None and str(sr) == str(exclude_faculty_id)):
                #frappe.log_error(title="Debug", message=f"Skipping {sr}")
                print("Continuing")
                continue
            print("Finished ", src)
            if min_sr is None or src <= min_count:
                min_count = src
                min_sr = sr
        print("Current secondary mins are ", min_count, min_sr)
        return min_pr, min_sr
    else:
        return min_pr, None

def _get_user_ignoring_perms(name):
    doc = frappe.get_doc("User", name)
    doc.flags.ignore_permissions = True
    return doc


def set_mentor_and_reviewer_roles():
    # Make sure that all current mentors and reviewers have the right roles set and
    # those that are not do not have this role.
    #
    # This runs from IRBProject.on_change() — i.e. under whichever user
    # (student/mentor/reviewer) just saved a project — but it syncs role
    # assignments for OTHER users system-wide based on global project
    # state, which a non-admin has no doctype permission to do. Without
    # ignore_permissions, add_roles()/remove_roles() below throws
    # PermissionError for any non-admin save, which aborts the rest of
    # on_change() (notifications) and, from the API caller's point of
    # view, makes the whole save() call look like it failed even though
    # the status field itself was already committed — the frontend never
    # gets a clean response to refresh from.

    # User.add_roles()/remove_roles() save the user unconditionally, and this
    # runs on every IRB Project save — so only touch users whose roles
    # actually change. Re-saving every mentor/reviewer each time made bulk
    # student uploads (one project save per CSV row) crawl.
    for link_field, role in (
        ("primary_reviewer", "Primary IRB Reviewer"),
        ("secondary_reviewer", "Secondary IRB Reviewer"),
        ("faculty_mentor", "Faculty Mentor"),
    ):
        _sync_role_holders(link_field, role)


def _sync_role_holders(link_field, role):
    """Give `role` to every user linked via `link_field` on an unapproved
    project, and take it from users with that role profile who no longer are."""
    current = set(frappe.db.sql_list(
        f"""select distinct u.name from tabUser as u join `tabIRB Project` as p join tabFaculty as f
        where p.{link_field} is not null and p.status != "Approved" and
        p.{link_field}=f.name and f.system_user=u.email"""
    ))
    if not current:
        return

    has_role = set(frappe.db.sql_list(
        "select parent from `tabHas Role` where parenttype='User' and role=%s", role
    ))
    for name in current - has_role:
        _get_user_ignoring_perms(name).add_roles(role)

    profile_holders = set(frappe.get_all(
        "User", filters={"enabled": 1, "role_profile_name": role}, pluck="name"
    ))
    for name in (profile_holders & has_role) - current:
        _get_user_ignoring_perms(name).remove_roles(role)


def send_email_if_configured(email_template, params, recipient_list):
	# Fetch the default outgoing email account
	default_email_account = frappe.db.get_value("Email Account", {
		"default_outgoing": 1,
		"enable_outgoing": 1
	}, "name")

	# Check if an account exists
	if default_email_account:
		# Callers run inside a document save (e.g. IRBProject.on_change); a
		# missing template must skip the e-mail, not fail the save.
		if not frappe.db.exists("Email Template", email_template):
			frappe.log_error(
				title=f"Email Template '{email_template}' not found",
				message=f"E-mail not sent to {recipient_list} with params {params}",
			)
			return
		email_template_doc = frappe.get_doc("Email Template", email_template)
		rendered_content = frappe.render_template(email_template_doc.response_, params)
		rendered_subject = frappe.render_template(email_template_doc.subject, params)
		frappe.sendmail(
			subject = rendered_subject,
			content = rendered_content,
			recipients=recipient_list,
			delayed=False
		)
	else:
		frappe.logger().info("Default email account not set")