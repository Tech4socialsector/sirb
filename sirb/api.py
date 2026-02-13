import frappe
from frappe.model.document import Document
from sirb.utils import get_logged_in_doc
import frappe
import csv
from frappe.utils.file_manager import get_file_path


def import_student_irb_information(logged_in_user, file_url, irb_unit):
    file_path = get_file_path(file_url.split('/')[-1])

    from sirb.utils import get_reviewers
    # print(logged_in_user)
    with open(file_path, 'r') as f:
        # We read lines first to get the total count for the progress bar
        rows = list(csv.DictReader(f))
        total_rows = len(rows)
        limit_student_count = 1
        for i, row in enumerate(rows):
            keys = row.keys()
            student_emails = []
            mentor_email = None
            mentor_name = None
            print(row)
            for key in keys:
                if key.lower().startswith("student-email-"):
                    student_emails.append(row[key])
                if key.lower().startswith("mentor-email"):
                    mentor_email = row[key]
                if key.lower().startswith("mentor-name"):
                    mentor_name = row[key]
            error = False
            try:
                project = None
                irb_unit_doc = frappe.get_doc("IRB Unit", irb_unit)
                mentor_required = irb_unit_doc.mentor_required
                if mentor_required:
                    if (not mentor_name) or (not mentor_email):
                        raise Exception("Mentor email and name are required for this IRB Unit")
                    existing_mentor_users = frappe.get_all("User", filters = {
                        "email": mentor_email
                    }, fields = ["name"])
                    print("Existing mentor users ", existing_mentor_users)
                    if not existing_mentor_users:
                        mentor_user = frappe.get_doc({
                            "doctype": "User",
                            "email": mentor_email,
                            "first_name": mentor_name,
                            "send_welcome_email" : 0
                        })
                    else:
                        mentor_user = frappe.get_doc("User", existing_mentor_users[0]["name"])
                    print("Adding faculty role")
                    mentor_user.add_roles("Faculty Member")
                    mentor_user.save(ignore_permissions = True)
                    frappe.db.commit()                  
                    print("Added faculty role")
                    existing_faculty = frappe.get_all("Faculty", filters = {
                        'system_user': mentor_user.name
                    }, fields = ["name"])
                    print("Existing faculty ", existing_faculty)
                    if not existing_faculty:
                        faculty_mentor = frappe.get_doc({
                            "doctype": "Faculty",
                            "system_user": mentor_user.name,
                            "full_name": mentor_name
                        })
                        faculty_mentor.save()
                    else:
                        faculty_mentor = frappe.get_doc("Faculty", existing_faculty[0]["name"])

                project = frappe.get_doc({
                    "doctype": "IRB Project",
                    "irb_unit": irb_unit,
                    "owner": logged_in_user
                })
                pr_reviewer, sr_reviewer = get_reviewers(irb_unit, None)
                if pr_reviewer is None:
                    raise Exception("Could not auto assign a primary reviewer - none available.")
                num_reviewers = int(irb_unit_doc.number_of_irb_reviewers_for_a_project)
                project.primary_reviewer = pr_reviewer
                if num_reviewers == 2:
                    if sr_reviewer is None:
                        raise Exception("Could not auto assign a secondary reviewer - none available.")                    
                    project.secondary_reviewer = sr_reviewer
                if mentor_required:
                    project.faculty_mentor = faculty_mentor.name
                print("Reviewers ", pr_reviewer, sr_reviewer)
                project.save()
                frappe.db.commit()
                print("Created project")
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Hard failure")
                if project:
                    frappe.delete_doc("IRB Project", project.name)
                status_msg = f"Failed to upload student information: {str(e)}"
                print(e)
                progress = 100
                message = {"progress": progress,
                        "status" : status_msg}
                if error:
                    message["error"] =  1
                print("Sending realtime to ", logged_in_user)
                frappe.publish_realtime(
                    event = "sirb_student_import_progress",
                    user = logged_in_user,
                    message = message
                )
                print("Sent realtime")                
                return
            try:
                for student_email in student_emails:
                    print("Processing ", student_email)
                    existing_users = frappe.get_all("User", filters = {
                        "email": student_email
                    }, fields = ["name"])
                    print("Existing users ", existing_users)
                    if not existing_users:
                        user = frappe.get_doc({
                            "doctype": "User",
                            "email": student_email,
                            "first_name": student_email,
                            "send_welcome_email" : 0,
                        })
                        print("Adding role")
                        user.add_roles("Student")          
                        user.save(ignore_permissions = True)
                        frappe.db.commit()
                    else:
                        user = frappe.get_doc("User", existing_users[0]["name"])
                                
                    existing_students = frappe.get_all("Student", filters = {
                        'system_user': user.name
                    }, fields = ["name"])
                    print("Existing students ", existing_students)
                    print(user, user.name)
                    if not existing_students:
                        print("Creating student")
                        student = frappe.get_doc({
                            "doctype": "Student",
                            "system_user": user.name,
                        })
                        student.save()
                    else:
                        student = frappe.get_doc("Student", existing_students[0]["name"])
                    print("Created Student")

                    existing_student_projects = frappe.get_all("Student Project Mapping", filters = {
                        "student": student.name,
                        "status": "active"
                    })
                    if existing_student_projects:
                        raise Exception(f"{user.name} has an existing active project.")
                    else:
                        print("Creating student project with ", student.name, project.name)                        
                        sp = frappe.get_doc({
                            "doctype": "Student Project Mapping",
                            "status": "active",
                            "student": student.name,
                            "irb_project": project.name
                        })
                        sp.save()
                        print("Created student project")
                    frappe.db.commit()
            except Exception as e:
                if project:
                    frappe.delete_doc("IRB Project", project.name)                
                frappe.log_error(frappe.get_traceback(), "Hard failure")
                status_msg = f"Failed to upload {student_email}: {str(e)}"
                print("Status message is ", status_msg)
                error = True
            else:
                print("NO ERROR")
                status_msg = f"Successfully uploaded {student_email}"
                print("Status message is ", status_msg)
                error = False
            finally:
                progress = int(((i+1)/total_rows)*100)
                message = {"progress": progress,
                        "status" : status_msg}
                if error:
                    message["error"] =  1
                print("Sending realtime to ", logged_in_user)
                frappe.publish_realtime(
                    event = "sirb_student_import_progress",
                    user = logged_in_user,
                    message = message
                )
                print("Sent realtime")
                print(message)
                if i+1 == limit_student_count:
                    return            

@frappe.whitelist()
def enque_student_upload(file_url, irb_unit):
    # 1. Enqueue the job to the background worker
    frappe.enqueue(
        import_student_irb_information,
        now=False,
        logged_in_user = frappe.session.user,
        file_url=file_url,
        irb_unit = irb_unit,
    )
    return "Upload Started"

def import_faculty_list(logged_in_user, file_url, ao_unit):
    faculty_name_field = "Faculty name"
    faculty_email_field = "Faculty's email ID"
    file_path = get_file_path(file_url.split('/')[-1])
    limit_faculty_count = 5
    with open(file_path, 'r') as f:
        rows = list(csv.DictReader(f))
        total_rows = len(rows)
        successful_faculty_count = 0
        
        ao_unit_doc = frappe.get_doc("Academic Organizational Unit", ao_unit)
        if not ao_unit_doc:
            message = {"progress": 100,
                    "status" : "Specified Academic Organizational Unit does not exist"}
            message["error"] =  1
            print("Sending realtime to ", logged_in_user)                    
            frappe.publish_realtime(
                event = "sirb_faculty_import_progress",
                user = logged_in_user,
                message = message
            )
            return
        for i, row in enumerate(rows):
            try:
                print(row)
                existing_faculty_users = frappe.get_all("User", filters = {
                    "email": row[faculty_email_field]
                }, fields = ["name"])
                print("Existing faculty users ", existing_faculty_users)
                if not existing_faculty_users:
                    user = frappe.get_doc({
                        "doctype": "User",
                        "email": row[faculty_email_field],
                        "first_name": row[faculty_name_field],
                        "send_welcome_email" : 0
                    })
                    print("Adding role")
                    user.add_roles("Faculty Member")          
                    user.save(ignore_permissions = True)
                    frappe.db.commit()
                else:
                    user = frappe.get_doc("User", existing_faculty_users[0]["name"])
                            
                existing_faculty = frappe.get_all("Faculty", filters = {
                    'system_user': row[faculty_email_field]
                }, fields = ["name"])
                print("Existing faculty ", existing_faculty)
                if not existing_faculty:
                    faculty = frappe.get_doc({
                        "doctype": "Faculty"
                    })
                else:
                    faculty = frappe.get_doc("Faculty", existing_faculty[0]["name"])

                faculty.system_user = user.name
                faculty.full_name = row[faculty_name_field]
                if not existing_faculty:
                    faculty.full_name = user.name
                faculty.save()

                existing_faculty_ao_unit_entries = frappe.get_all("Faculty Academic Organizational Unit", filters = {
                    "faculty_member": faculty.name,
                    "ao_unit": ao_unit
                })
                if not existing_faculty_ao_unit_entries:
                    f_ao_unit = frappe.get_doc({
                        "doctype": "Faculty Academic Organizational Unit",
                        "faculty_member": faculty.name,
                        "ao_unit": ao_unit_doc.name
                    })
                    f_ao_unit.save()
                frappe.db.commit()
                
            except Exception as e:
                status_msg = f"Failed to upload {row[faculty_email_field]}: {str(e)}"
                error = True
            else:
                successful_faculty_count += 1
                status_msg = f"Successfully uploaded {row[faculty_email_field]}"
                error = False
            finally:
                progress = int(((i+1)/total_rows)*100)
                message = {"progress": progress,
                        "status" : status_msg}
                if error:
                    message["error"] =  1
                print("Sending realtime to ", logged_in_user)                    
                frappe.publish_realtime(
                    event = "sirb_faculty_import_progress",
                    user = logged_in_user,
                    message = message
                )
                print("Sent realtime")                
                if i+1 == limit_faculty_count:
                    break


@frappe.whitelist()
def enque_faculty_upload(file_url, ao_unit):
    # 1. Enqueue the job to the background worker
    frappe.enqueue(
        import_faculty_list,
        now=False,
        logged_in_user = frappe.session.user,
        file_url=file_url,
        ao_unit = ao_unit,
    )
    return "Upload Started"


@frappe.whitelist()
def set_project_status(project_id, status):
    project = frappe.get_doc("IRB Project", project_id)
    project.status = status
    project.save()
    frappe.db.commit()
    return {'message': "Success"}

def get_mentor_project_count(type):
    doc = get_logged_in_doc("Faculty")
    print("doc is ", doc)   
    if doc:
        if type == "unapproved":
            query = f'''select count(*) as count from tabStudent as s 
            join `tabStudent Project Mapping` as sp join `tabIRB Project` as p join 
            tabFaculty as f on s.name = sp.student and sp.irb_project = p.name  
            and p.faculty_mentor = f.name 
            where p.status not in ("Approved") and sp.status="active"
            and f.system_user = "{doc.system_user}"'''
            #print(query)
            data = frappe.db.sql(
                query, as_dict=1
            )        
        elif type == "pending":
            query = f'''select count(*) as count from tabStudent as s 
            join `tabStudent Project Mapping`
            as sp join `tabIRB Project` as p join tabFaculty as f on s.name = sp.student 
            and sp.irb_project = p.name  
            and p.faculty_mentor = f.name
            where p.status='Awaiting Faculty mentor approval'
            and f.system_user = "{doc.full_name}"  and sp.status="active"'''
        else:
            return None
    else:
        return None
    #print(query)
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
    print(return_dict)
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

def get_reviewer_project_count(type, role):
    doc = get_logged_in_doc("Faculty")
    if doc:
        if type == "unapproved":
            if role == "Primary Reviewer":
                query = f'''select count(*) as count from tabStudent as s join `tabStudent Project Mapping`
                as sp join `tabIRB Project` as p join tabFaculty as f on s.name = sp.student 
                and sp.irb_project = p.name  
                and f.name  = p.primary_reviewer
                where p.status !='Approved' and sp.status="active"
                and f.system_user = "{doc.system_user}"'''
            elif role == "Secondary Reviewer":
                query = f'''select count(*) as count from tabStudent as s join `tabStudent Project Mapping`
                as sp join `tabIRB Project` as p join tabFaculty as f on s.name = sp.student
                and sp.irb_project = p.name  
                and f.name  = p.secondary_reviewer
                where p.status !='Approved' and sp.status="active"
                and f.system_user = "{doc.system_user}"'''                
        elif type == "pending":
            if role == "Primary Reviewer":            
                query = f'''select count(*) as count from tabStudent as s join `tabStudent Project Mapping`
                as sp join `tabIRB Project` as p join tabFaculty as f on s.name = sp.student 
                and sp.irb_project = p.name  
                and f.name  = p.primary_reviewer
                where p.status in ('Awaiting primary reviewer comments', 'Awaiting final approval', 'Awaiting reviewer feedback to student')
                and f.system_user = "{doc.system_user}" and sp.status="active"'''
            elif role == "Secondary Reviewer":
                query = f'''select count(*) as count from tabStudent as s join `tabStudent Project Mapping`
                as sp join `tabIRB Project` as p join tabFaculty as f on s.name = sp.student 
                and sp.irb_project = p.name  
                and f.name  = p.secondary_reviewer
                where p.status='Awaiting secondary reviewer comments' and sp.status="active"
                and f.system_user = "{doc.system_user}"'''                
        else:
            return None
    else:
        return None
    print(query)
    data = frappe.db.sql(
        query, as_dict=1
    )
    return data

    
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

@frappe.whitelist()
def get_irb_project_roles(user, project_name):
    is_student = False
    is_mentor = False
    is_primary_reviewer = False
    is_secondary_reviewer = False
    query = f'''
    select s.name as student_id, p.faculty_mentor as mentor_id, p.primary_reviewer as primary_reviewer, 
    p.secondary_reviewer as secondary_reviewer from tabStudent as s join `tabIRB Project` as p 
    join `tabStudent Project Mapping` as sp where sp.student = s.name and sp.status="active" and
    sp.irb_project = p.name and p.name = "{project_name}"
    '''
    project_info = frappe.db.sql(query, as_dict = 1)
    # print(project_info)
    if project_info:
        for p in project_info:
            query = f''' select u.email from tabStudent as s join tabUser as u where 
            s.system_user = u.name and u.email = "{user}" and s.name = "{p["student_id"]}"'''
            results = frappe.db.sql(query)
            print(results)
            if results:
                is_student = True
            query = f''' select u.email from tabFaculty as f join tabUser as u where 
            f.system_user = u.email and u.email = "{user}" and f.name = "{p["mentor_id"]}"'''
            results = frappe.db.sql(query)
            print(results)
            if results:
                is_mentor = True
            query = f''' select u.email from tabFaculty as f join tabUser as u where 
            f.system_user = u.email and u.email = "{user}" and f.name = "{p["primary_reviewer"]}"'''
            results = frappe.db.sql(query)
            print(results)
            if results:
                is_primary_reviewer = True
            query = f''' select u.email from tabFaculty as f join tabUser as u where 
            f.system_user = u.email and u.email = "{user}" and f.name = "{p["secondary_reviewer"]}"'''
            results = frappe.db.sql(query)
            print(results)
            if results:
                is_secondary_reviewer = True
    ret_dict = {
        "is_student": is_student, 
        "is_mentor": is_mentor, 
        "is_primary_reviewer":  is_primary_reviewer, 
        "is_secondary_reviewer": is_secondary_reviewer
    }
    print(ret_dict)
    return ret_dict

# WAS USED WHEN I TRIED WEB FORMS NOT USING NOW BUT KEEPING IT JUST IN CASE
# @frappe.whitelist()
# def get_field_permissions_from_doctype(doctype):
#     meta = frappe.get_meta(doctype)
#     user = frappe.session.user
#     perms = {}

#     for df in meta.fields:
#         print(df.fieldname)
#         permlevel = df.permlevel or 0
#         read_allowed = meta.has_permlevel_access_to(fieldname=df.fieldname, df=df, permission_type="read")
#         write_allowed = meta.has_permlevel_access_to(fieldname=df.fieldname, df=df, permission_type="write")
#         print(read_allowed, write_allowed)
#         perms[df.fieldname] = {
#             "read": read_allowed,
#             "write": write_allowed and not df.read_only
#         }
#     return perms

# NO LONGER BEING USED BECAUSE THE PROJECTS ARE CREATED DURING STUDENT UPLOAD
# @frappe.whitelist()
# def create_student_project(student_id, title):
#     #print(frappe.session.user)
#     project = frappe.get_doc({
#         'doctype': 'IRB Project',
#         'title': title,
#     })
#     project.insert()
#     student = frappe.get_doc("Student", student_id)
#     p = student.append("projects", {
#         "project": project.name
#     })
#     student.save()
#     frappe.db.commit()

#     return {'message': project.name}  # Return the Project ID as a response

# NO LONGER BEING USED BECAUSE THE MENTORS ARE ASSIGNED DURING UPLOAD
# @frappe.whitelist()
# def assign_student_mentor(student, project, mentor):
#     st = frappe.get_doc("Student", student)
#     for p in st.projects:
#         if p.project == project:
#             p.full_name = mentor
#     st.save()
#     pr = frappe.get_doc("IRB Project", project)
#     pr.status = "Awaiting Faculty mentor approval"
#     pr.save()
#     frappe.db.commit()
#     return {'message': "Success"}

# NO LONGER BEING USED
# @frappe.whitelist()
# def mentor_approve_project(project_id):
#     project = frappe.get_doc("Project", project_id)
#     #print(project)
#     project.status = "Awaiting reviewer assignment"
#     project.save()
#     frappe.db.commit()
#     return {'message': "Success"}

# NO LONGER BEING USED
# @frappe.whitelist()
# def submit_mentor_feedback(project_id, feedback, faculty_id):
#     project = frappe.get_doc("IRB Project", project_id)
#     faculty = frappe.get_doc("Faculty", faculty_id)
#     #print(faculty.full_name)
#     #print(faculty.name)
#     #print(faculty.display_full_name)
#     new_comment = frappe.new_doc("Faculty Comment")
#     new_comment.update({
#         "facultys_comments":  feedback,
#         "facultys_name": faculty.display_full_name,
#         "facultys_role": "Faculty Member"
#     })
#     project.mentors_feedback.append(new_comment)
#     project.status = "Awaiting student correction for mentor feedback"
#     project.save()
#     frappe.db.commit()
#     return {'message': "Success"}


# NO LONGER BEING USED
# @frappe.whitelist()
# def assign_student_reviewers(project_id, primary_reviewer, secondary_reviewer):
#     project = frappe.get_doc("Project", project_id)
#     if primary_reviewer != "":
#         project.primary_reviewer = int(primary_reviewer)
#     if secondary_reviewer != "":
#         project.secondary_reviewer = int(secondary_reviewer)
#     project.status = "Awaiting reviewer feedback"
#     project.save()
#     frappe.db.commit()
#     return {'message': "Success"}