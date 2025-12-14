import frappe

def map_user():
    roles = frappe.get_roles(frappe.session.user)
    user = frappe.session.user
    if "Student" in roles:
        frappe.local.response["home_page"] = f"/student_home"
        # Set default workspace for Student role if not already set
        if frappe.db.exists("Workspace", "Student Workspace"):
            user_doc = frappe.get_doc("User", user)
            if not user_doc.default_workspace:
                frappe.db.set_value("User", user, "default_workspace", "Student Workspace")
                frappe.db.commit()
    elif "Faculty Mentor" in roles:
        frappe.local.response["home_page"] = f"/faculty_mentor_home"
    elif "Anchor" in roles:
        frappe.local.response["home_page"] = f"/anchor_home"
    elif "Primary Reviewer" in roles or "Secondary Reviewer" in roles:
        frappe.local.response["home_page"] = f"/reviewer_home"

