
import frappe

def get_logged_in_doc(role_name):
    user = frappe.session.user
    role_doc_mapping = {
        "Faculty Mentor" : "Faculty",
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
        f'''select p.primary_reviewer, count(*) as count from `tabIRB Project` as p where 
        p.primary_reviewer is not null and p.irb_unit = "{irb_unit}" and p.status != "Approved" 
        group by p.primary_reviewer;''', as_dict=1
    )
    print(primary_reviewer_data)
    for d in primary_reviewer_data:
        # primary_reviewers_with_projects.add(d["primary_reviewer"])
        project_count_for_primary_reviewers[d["primary_reviewer"]] += d["count"]

    min_count = 0
    min_pr = None
    print("Project count for primary reviewers - ", project_count_for_primary_reviewers)
    
    for pr, prc in project_count_for_primary_reviewers.items():
        if pr == exclude_faculty_id:
            continue
        if prc <= min_count:
            min_count = prc
            min_pr = pr
    print("Current primary mins are ", min_count, min_pr)

    if num_reviewers == 2:
        print("Checking secondary")
        secondary_reviewer_data = frappe.db.sql(
            f'''select p.secondary_reviewer, count(*) as count from `tabIRB Project` as p where 
            p.secondary_reviewer is not null and p.irb_unit = "{irb_unit}" and p.status != "Approved" 
            group by p.secondary_reviewer;''', as_dict=1
        )
        for d in secondary_reviewer_data:
            # secondary_reviewers_with_projects.add(d["secondary_reviewer"])
            project_count_for_secondary_reviewers[d["secondary_reviewer"]] += d["count"]
        min_count = 0
        min_sr = None
        print(project_count_for_secondary_reviewers)
        for sr, src in project_count_for_secondary_reviewers.items():
            print(sr, src)
            if sr == pr or pr == exclude_faculty_id:
                print("Continuing")
                continue
            print("Finished ", src)
            if src <= min_count:
                min_count = src
                min_sr = sr
        print("Current secondary mins are ", min_count, min_sr)
        return min_pr, min_sr
    else:
        return min_pr, None

def set_reviewer_roles():
    # Make sure that all current reviewers have the right reviewer roles set and
    # those that are not do not have this role.

    # Get all current primary reviewers
    query = '''
        select u.email from tabUser as u join `tabIRB Project` as p join tabFaculty as f
        where p.primary_reviewer is not null and p.status != "Approved" and 
        p.primary_reviewer=f.name and f.system_user=u.email'''
    result = frappe.db.sql(query, as_list=1)
    prs = [pr[0] for pr in result]
    print("Primary reviewers - ", prs)
    pr_docs = {p: frappe.get_doc("User", p) for p in prs}

    print(pr_docs)
    for _,p in pr_docs.items():
        print("Adding for ", p)
        p.add_roles("Primary IRB Reviewer")

    all_prs = frappe.db.get_all(
        "Has Role",
        filters={"role": "Primary IRB Reviewer"},
        pluck="parent"
    )
    all_prs_docs = {p: frappe.get_doc("User", p) for p in all_prs}
    print(pr_docs, all_prs_docs)
    for id, user in all_prs_docs.items():
        if id not in pr_docs:
            print("Removing for ", user)
            user.remove_roles("Primary IRB Reviewer")

    # Get all current secondary reviewers
    query = '''
        select u.email from tabUser as u join `tabIRB Project` as p join tabFaculty as f
        where p.secondary_reviewer is not null and p.status != "Approved" and 
        p.secondary_reviewer=f.name and f.system_user=u.email'''
    result = frappe.db.sql(query, as_list=1)
    srs = [sr[0] for sr in result]
    print("Secondary reviewers - ", srs)
    secondary_reviewers = {s: frappe.get_doc("User", s) for s in srs}
    for _, s in secondary_reviewers.items():
        s.add_roles("Secondary IRB Reviewer")
                             
    all_srs = frappe.db.get_all(
        "Has Role",
        filters={"role": "Secondary IRB Reviewer"},
        pluck="parent"  
    )
    all_srs_docs = {s: frappe.get_doc("User", s) for s in all_srs}
    for _, user in all_srs_docs.items():
        if user not in secondary_reviewers:
            user.remove_roles("Secondry IRB Reviewer")
