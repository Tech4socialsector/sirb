import frappe

def get_context(context):
    user = frappe.session.user

    if not user or user == "Guest":
        context["logged_in"] = False
        return
    else:
        context["logged_in"] = True

    roles = frappe.get_roles(user)
    
    if "Student" in roles:
        context["redirect"] = "/student_home"
        context["owner"] = "student"
    elif "Faculty Mentor" in roles:
        context["redirect"] =  f"/faculty_mentor_home"
        context["owner"] = "faculty mentor"
    elif "Anchor" in roles:
        context["redirect"] =  f"/anchor_home"
        context["owner"] = "anchor"
    elif "Primary Reviewer" in roles or "Secondary Reviewer" in roles:
        context["redirect"] =  f"/reviewer_home"
        context["owner"] = "reviewer"