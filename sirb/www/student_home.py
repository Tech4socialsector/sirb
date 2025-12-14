import frappe

def get_context(context):
    roles = frappe.get_roles(frappe.session.user)
    if "Student" in roles:
        context["is_student"] = True
    else:
        context["is_student"] = False

    user = frappe.session.user
    print(user)
    students = frappe.db.get_all("Student", filters =  {
        "full_name": user
    })
    student = None
    if students:
        student = frappe.get_doc("Student", students[0]["name"])
        project_list = []
        for project_link in student.projects:
            project = frappe.get_doc("Project", project_link.project)
            project_list.append(project)
            context["projects"] = project_list
    context["student"] = student
