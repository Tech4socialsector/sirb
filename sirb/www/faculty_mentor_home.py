import frappe

def get_context(context):
    user = frappe.session.user
    #print(user)
    all_students = frappe.db.get_all("Student")
    student_list = []
    for s in all_students:
        sdoc = frappe.get_doc("Student", s["name"])
        if sdoc.projects:
            for p in sdoc.projects:
                print(p.full_name)
                flist = frappe.db.get_all("Faculty", filters = {
                    "name": p.full_name
                }, fields = ["full_name"])
                print(flist)
                if flist:
                    for f in flist:
                        if f["full_name"] == user:
                            student_list.append(s)
                            break
            #project_list = frappe.db.get_all("Project")
    
    print(student_list)
    mentor_list = frappe.db.get_all("Faculty", filters = {
        "full_name": user
    })
    context["faculty_id"] = mentor_list[0]["name"]
    students = []
    for student in student_list:
        sdoc = frappe.get_doc("Student", student["name"])
        projects = []
        for plink in sdoc.projects:
            proj = frappe.get_doc("Project", plink)
            projects.append(proj)
        students.append({"student": sdoc, "projects": projects})
    context["students"] = students
    #print(context["students"])