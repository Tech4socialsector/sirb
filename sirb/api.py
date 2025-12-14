import frappe
from frappe.model.document import Document
from sirb.utils import get_logged_in_doc

@frappe.whitelist()
def get_field_permissions_from_doctype(doctype):
    meta = frappe.get_meta(doctype)
    user = frappe.session.user
    perms = {}

    for df in meta.fields:
        print(df.fieldname)
        permlevel = df.permlevel or 0
        read_allowed = meta.has_permlevel_access_to(fieldname=df.fieldname, df=df, permission_type="read")
        write_allowed = meta.has_permlevel_access_to(fieldname=df.fieldname, df=df, permission_type="write")
        print(read_allowed, write_allowed)
        perms[df.fieldname] = {
            "read": read_allowed,
            "write": write_allowed and not df.read_only
        }
    return perms

@frappe.whitelist()
def create_student_project(student_id, title):
    #print(frappe.session.user)
    # Create a new Student Project document
    project = frappe.get_doc({
        'doctype': 'Project',
        'title': title,
    })
    project.insert()
    student = frappe.get_doc("Student", student_id)
    p = student.append("projects", {
        "project": project.name
    })
    student.save()
    frappe.db.commit()

    return {'message': project.name}  # Return the Project ID as a response

@frappe.whitelist()
def assign_student_mentor(student, project, mentor):
    st = frappe.get_doc("Student", student)
    for p in st.projects:
        if p.project == project:
            p.full_name = mentor
    st.save()
    pr = frappe.get_doc("Project", project)
    pr.status = "Awaiting Faculty mentor approval"
    pr.save()
    frappe.db.commit()
    return {'message': "Success"}

@frappe.whitelist()
def mentor_approve_project(project_id):
    project = frappe.get_doc("Project", project_id)
    #print(project)
    project.status = "Awaiting reviewer assignment"
    project.save()
    frappe.db.commit()
    return {'message': "Success"}

@frappe.whitelist()
def submit_mentor_feedback(project_id, feedback, faculty_id):
    project = frappe.get_doc("Project", project_id)
    faculty = frappe.get_doc("Faculty", faculty_id)
    #print(faculty.full_name)
    #print(faculty.name)
    #print(faculty.display_full_name)
    new_comment = frappe.new_doc("Faculty Comment")
    new_comment.update({
        "facultys_comments":  feedback,
        "facultys_name": faculty.display_full_name,
        "facultys_role": "Faculty Mentor"
    })
    project.mentors_feedback.append(new_comment)
    project.status = "Awaiting student correction for mentor feedback"
    project.save()
    frappe.db.commit()
    return {'message': "Success"}

@frappe.whitelist()
def assign_student_reviewers(project_id, primary_reviewer, secondary_reviewer):
    project = frappe.get_doc("Project", project_id)
    if primary_reviewer != "":
        project.primary_reviewer = int(primary_reviewer)
    if secondary_reviewer != "":
        project.secondary_reviewer = int(secondary_reviewer)
    project.status = "Awaiting reviewer feedback"
    project.save()
    frappe.db.commit()
    return {'message': "Success"}

@frappe.whitelist()
def set_project_status(project_id, status):
    project = frappe.get_doc("Project", project_id)
    project.status = status
    project.save()
    frappe.db.commit()
    return {'message': "Success"}

def get_mentor_project_count(type):
    doc = get_logged_in_doc("Faculty Mentor")    
    if doc:
        if type == "unapproved":
            query = f'''select count(*) as count, sp.full_name from tabStudent as s join `tabStudent Project`
            as sp join tabProject as p join tabFaculty as f on s.name = sp.parent and sp.project = p.name  
            and sp.full_name = f.name 
            where p.status not in ("Approved")
            and f.full_name = "{doc.full_name}"'''
            #print(query)
            data = frappe.db.sql(
                query, as_dict=1
            )        
        elif type == "pending":
            query = f'''select count(*) as count, sp.full_name from tabStudent as s join `tabStudent Project`
            as sp join tabProject as p join tabFaculty as f on s.name = sp.parent and sp.project = p.name  
            and sp.full_name = f.name 
            where p.status='Awaiting Faculty mentor approval'
            and f.full_name = "{doc.full_name}"'''
        else:
            return None
    else:
        return None
    #print(query)
    data = frappe.db.sql(
        query, as_dict=1
    )
    return data

def get_reviewer_project_count(type, role):
    doc = get_logged_in_doc("Faculty")
    if doc:
        if type == "unapproved":
            if role == "Primary Reviewer":
                query = f'''select count(*) as count, sp.full_name from tabStudent as s join `tabStudent Project`
                as sp join tabProject as p join tabFaculty as f on s.name = sp.parent and sp.project = p.name  
                and f.name  = p.primary_reviewer
                where p.status !='Approved'
                and f.full_name = "{doc.full_name}"'''
            elif role == "Secondary Reviewer":
                query = f'''select count(*) as count, sp.full_name from tabStudent as s join `tabStudent Project`
                as sp join tabProject as p join tabFaculty as f on s.name = sp.parent and sp.project = p.name  
                and f.name  = p.secondary_reviewer
                where p.status !='Approved'
                and f.full_name = "{doc.full_name}"'''                
        elif type == "pending":
            if role == "Primary Reviewer":            
                query = f'''select count(*) as count, sp.full_name from tabStudent as s join `tabStudent Project`
                as sp join tabProject as p join tabFaculty as f on s.name = sp.parent and sp.project = p.name  
                and f.name  = p.primary_reviewer
                where p.status='Awaiting reviewer feedback'
                and f.full_name = "{doc.full_name}"'''
            elif role == "Secondary Reviewer":
                query = f'''select count(*) as count, sp.full_name from tabStudent as s join `tabStudent Project`
                as sp join tabProject as p join tabFaculty as f on s.name = sp.parent and sp.project = p.name  
                and f.name  = p.secondary_reviewer
                where p.status='Awaiting reviewer feedback'
                and f.full_name = "{doc.full_name}"'''                
        else:
            return None
    else:
        return None
    # print(query)
    data = frappe.db.sql(
        query, as_dict=1
    )
    return data

@frappe.whitelist()
def get_mentor_pending_project_count():
    return_dict = {}
    data = get_mentor_project_count("pending")
    if data:
        return_dict["value"] = data[0]["count"]
        return_dict["fieldtype"] = "Int"
        return_dict["route"] = ["app", "query-report", "Mentor's pending worklist"]
    return return_dict

@frappe.whitelist()
def get_mentor_unapproved_project_count():
    return_dict = {}
    data = get_mentor_project_count("unapproved")
    if data:
        return_dict["value"] = data[0]["count"]
        return_dict["fieldtype"] = "Int"
        return_dict["route"] = ["app", "query-report", "All Mentor Projects"]
    return return_dict
    
@frappe.whitelist()
def get_primary_reviewer_unapproved_project_count():
    return_dict = {}
    data = get_reviewer_project_count("unapproved", "Primary Reviewer")
    if data:
        return_dict["value"] = data[0]["count"]
        return_dict["fieldtype"] = "Int"
        return_dict["route"] = ["app", "query-report", "All Primary Reviewer Projects"]
    return return_dict

@frappe.whitelist()
def get_secondary_reviewer_unapproved_project_count():
    return_dict = {}
    data = get_reviewer_project_count("unapproved", "Secondary Reviewer")
    if data:
        return_dict["value"] = data[0]["count"]
        return_dict["fieldtype"] = "Int"
        return_dict["route"] = ["app", "query-report", "All Secondary Reviewer Projects"]
    return return_dict

@frappe.whitelist()
def get_primary_reviewer_pending_project_count():
    return_dict = {}
    data = get_reviewer_project_count("pending", "Primary Reviewer")
    if data:
        return_dict["value"] = data[0]["count"]
        return_dict["fieldtype"] = "Int"
        return_dict["route"] = ["app", "query-report", "Primary Reviewer's pending worklist"]
    return return_dict

@frappe.whitelist()
def get_secondary_reviewer_pending_project_count():
    return_dict = {}
    data = get_reviewer_project_count("pending", "Secondary Reviewer")
    if data:
        return_dict["value"] = data[0]["count"]
        return_dict["fieldtype"] = "Int"
        return_dict["route"] = ["app", "query-report", "Secondary Reviewer's pending worklist"]
    return return_dict