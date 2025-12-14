import frappe

def get_context(context):
    roles = frappe.get_roles(frappe.session.user)
    user = frappe.session.user
    print(user)
    fd = frappe.db.get_all("Faculty", filters = {
        "full_name": user
    })
    fdoc = frappe.get_doc("Faculty", fd[0]["name"])


    is_primary_reviewer = False
    is_secondary_reviewer = False

    if "Primary Reviewer" in roles:
        is_primary_reviewer = True
    if "Secondary Reviewer" in roles:
        is_secondary_reviewer = True
    
    assignment_list = []
    if is_primary_reviewer or is_secondary_reviewer:

        students = frappe.db.get_all("Student")
        faculty = frappe.db.get_all("Faculty")


        no_assignments = True
        for st in students:
            student = frappe.get_doc("Student", st["name"])
            primary_project_list = []
            secondary_project_list = []
            for sp in student.projects:
                project = frappe.get_doc("Project", sp.project)
                previewers = frappe.db.get_all("Project", filters={
                    "primary_reviewer": fd[0]["name"],
                    "status": ["in", ["Awaiting reviewer feedback", "Awaiting student correction for reviewer feedback"]]
                })
                provisional_approvals = frappe.db.get_all("Project", filters={
                    "primary_reviewer": fd[0]["name"],
                    "status": "Provisionally approved"
                })
                previewers.extend(provisional_approvals)
                if previewers:
                    primary_project_list.append(project)
                    no_assignments = False                    
                sreviewers = frappe.db.get_all("Project", filters={
                    "secondary_reviewer": fd[0]["name"],
                    "status": ["in", ["Awaiting reviewer feedback", "Awaiting student correction for reviewer feedback"]]
                })
                if sreviewers:
                    secondary_project_list.append(project)
                    no_assignments = False
               
            if primary_project_list or secondary_project_list:
                assignment_list.append({
                    "student": student, 
                    "primary_project_list": primary_project_list, 
                    "secondary_project_list": secondary_project_list
                })
    
    print(assignment_list)
    print(no_assignments)
    context["assignment_list"] = assignment_list
    context["no_assignments"] = no_assignments
    #print(context)
