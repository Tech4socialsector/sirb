import frappe

def get_context(context):
    students = frappe.db.get_all("Student")
    faculty = frappe.db.get_all("Faculty")
    print(faculty)
    faculty_mentors = []
    primary_reviewers = []
    secondary_reviewers = []
    for f in faculty:
        fdoc = frappe.get_doc("Faculty", f["name"])
        #print(fdoc.full_name)
        fusers = frappe.db.get_all("User", filters={"email": fdoc.full_name})
        fuser = frappe.get_doc("User", fusers[0]["name"])
        #print(fuser.name)
        roles = frappe.get_roles(fuser.name)
        #print(roles)        
        if "Faculty Mentor" in roles:
            faculty_mentors.append({"fid": fdoc.name, "fuser": fuser})
        if"Primary Reviewer" in roles:
            primary_reviewers.append({"fid": fdoc.name, "fuser": fuser})
        if "Secondary Reviewer" in roles:
            secondary_reviewers.append({"fid": fdoc.name, "fuser": fuser})
    context["faculty_mentors"] = faculty_mentors
    context["primary_reviewers"] = primary_reviewers
    context["secondary_reviewers"] = secondary_reviewers
    print(context["primary_reviewers"])
    print(context["secondary_reviewers"])

    #print(faculty)
    assignment_list = []
    no_mentor_assignments = True
    no_reviewer_assignments = True
    for st in students:
        student = frappe.get_doc("Student", st["name"])
        #print("student ", student)
        ma_project_list = []
        ra_project_list = []
        for sp in student.projects:
            project = frappe.get_doc("Project", sp.project)
            #print("Project ", project)
            if project.status == "Awaiting Faculty mentor assignment":
                ma_project_list.append(project)
                no_mentor_assignments = False
            elif project.status == "Awaiting reviewer assignment" or (project.primary_reviewer and not project.secondary_reviewer):
                ra_project_list.append(project)
                no_reviewer_assignments = False
        if ma_project_list or ra_project_list:
            assignment_list.append({
                "student": student, 
                "ma_project_list": ma_project_list, 
                "ra_project_list": ra_project_list
            })
    print(assignment_list)

    context["assignment_list"] = assignment_list
    context["no_mentor_assignments"] = no_mentor_assignments
    context["no_reviewer_assignments"] = no_reviewer_assignments
    #print(context)
