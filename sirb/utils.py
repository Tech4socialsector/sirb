
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
    print(doc_name)
    if doc_name:
        fentries = frappe.db.get_all(doc_name, filters = {
            "full_name": user
        })
        if fentries:
            doc = frappe.get_doc(doc_name, fentries[0]["name"])
            return doc
    return None
