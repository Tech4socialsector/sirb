// Copyright (c) 2025, Ram and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Project", {
// 	refresh(frm) {

// 	},
// });

var field_list = ["abstract"];
var extns = ["_mf", "_rf", "_rn", "_fc"]
var button_map = {}
for (var i=0;i< field_list.length;i++) {
    for (var j=0;j<extns.length;j++) {
        button_map[field_list[i]+extns[j]+"_button"] = field_list[i]+extns[j];
    }
}
var field_word_length_map = {
    "abstract": 1
}
// console.log(button_map);

function handleButtonClick(frm, fieldname) {
    let st = Boolean(frm.get_field(fieldname).df.hidden);
    frm.toggle_display(fieldname, st);
}

async function get_previous_login() {
    let res = await frappe.db.get_list("Activity Log",
        { fields: ["creation"], filters: { user: frappe.session.user, operation: "Login" }, order_by: "creation desc", limit: 2 });
    
    if(res.length > 1) return new Date(res[1].creation.replace(" ", "T"));
    return null;
}
async function get_versions_after_login(doctype, docname, prev_login_time) {
    let prev_login_str = prev_login_time.getFullYear() + '-' +
                            String(prev_login_time.getMonth() + 1).padStart(2, '0') + '-' +
                            String(prev_login_time.getDate()).padStart(2, '0') + ' ' +
                            String(prev_login_time.getHours()).padStart(2, '0') + ':' +
                            String(prev_login_time.getMinutes()).padStart(2, '0') + ':' +
                            String(prev_login_time.getSeconds()).padStart(2, '0');
    let versions = await frappe.db.get_list("Version",
        {
            fields: ["data", "modified"],
            filters: [
                ["docname", "=", docname],
                ["ref_doctype", "=", doctype],
                ["modified", ">", prev_login_str]
            ],
            order_by: "modified asc"
        });

    return versions;
}

function field_changed_since_last_login(versions, fieldname) {
    field_changed = false;
    for (let v of versions) {
        if (v.data) {
            let version_data = JSON.parse(v.data);
            for (let change of version_data.changed) {
                let fieldname = change[0];
                if (change[0] === fieldname) {
                    field_changed = true;
                    break;
                }
            }
        }
    }
    // alert(field_changed)
    return field_changed
}


frappe.ui.form.on("Project", {
    async refresh(frm) {
        $("#navbar-breadcrumbs").css({'visibility':'hidden'});
        let roles = frappe.user_roles;
        if (frm.doc.status === "Awaiting Faculty mentor approval") {
            if (roles.includes("Faculty Mentor")) {
                frm.add_custom_button("Approve for review", () => {
                    frappe.call({
                        method: "sirb.api.set_project_status",  // Python method
                        args: {
                            project_id: frm.doc.name,
                            status: "Awaiting reviewer assignment"
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                // frappe.msgprint("API executed successfully!");
                                frappe.set_route("app", "pending-projects")
                            }
                        }
                    });                    
                }, "Actions");
                frm.add_custom_button("Request corrections from student", () => {
                    frappe.call({
                        method: "sirb.api.set_project_status",  // Python method
                        args: {
                            project_id: frm.doc.name,
                            status: "Awaiting student correction for mentor feedback"
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                // frappe.msgprint("API executed successfully!");
                                frappe.set_route("app", "pending-projects")
                            }
                        }
                    });
                }, "Actions");
            }       
        } else if (["Awaiting student correction for mentor feedback", "Awaiting student correction for reviewer feedback"].includes(frm.doc.status)) {
            if (roles.includes("Student")) {
                frm.add_custom_button("Submit corrections", () => {
                    if (frm.doc.status == "Awaiting student correction for mentor feedback")
                        new_status = "Awaiting Faculty mentor approval";
                    else if (frm.doc.status == "Awaiting student correction for reviewer feedback")
                        new_status = "Awaiting reviewer feedback";
                    frappe.call({
                        method: "sirb.api.set_project_status",  // Python method
                        args: {
                            project_id: frm.doc.name,
                            status: new_status
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                // frappe.msgprint("API executed successfully!");
                                frappe.set_route("app", "pending-projects")
                            }
                        }
                    });                    
                }, "Actions");
            }
        } else if (frm.doc.status ==="Awaiting reviewer feedback") {
            if (roles.includes("Primary Reviewer") || roles.includes("Secondary Reviewer")) {
                frm.add_custom_button("Request corrections from student", () => {
                    frappe.call({
                        method: "sirb.api.set_project_status",  // Python method
                        args: {
                            project_id: frm.doc.name,
                            status: "Awaiting student correction for reviewer feedback"
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                // frappe.msgprint("API executed successfully!");
                                frappe.set_route("app", "pending-projects")
                            }
                        }
                    });                    
                }, "Actions");
                if (roles.includes("Primary Reviewer")) {
                    frm.add_custom_button("Grant FINAL approval", () => {
                        frappe.call({
                            method: "sirb.api.set_project_status",  // Python method
                            args: {
                                project_id: frm.doc.name,
                                status: "Approved"
                            },
                            callback: function(r) {
                                if (!r.exc) {
                                    // frappe.msgprint("API executed successfully!");
                                    frappe.set_route("app", "pending-projects")
                                }
                            }
                        });
                    }, "Actions");
                    frm.add_custom_button("Grant PROVISIONAL approval", () => {
                        frappe.call({
                            method: "sirb.api.set_project_status",  // Python method
                            args: {
                                project_id: frm.doc.name,
                                status: "Provisionally approved"
                            },
                            callback: function(r) {
                                if (!r.exc) {
                                    // frappe.msgprint("API executed successfully!");
                                    frappe.set_route("app", "pending-projects")
                                }
                            }
                        });
                    }, "Actions");
                }
            }
        }

        let last_login = await get_previous_login();
        // console.log(last_login);
        if(last_login) {
            let versions = await get_versions_after_login("Project", frm.doc.name, last_login);
            // console.log(versions);
            for (let fieldname of field_list) {
                if(field_changed_since_last_login(versions, fieldname)) {
                    // alert("!!")
                    label = frm.get_field(fieldname).df.label;
                    if (!label.includes("Changed"))
                        frm.set_df_property(fieldname, "label", label + " (Changed)");
                }
            }
        }

        if (frm.first_load === undefined) {
            frm.first_load = true;
            for (var i=0;i< field_list.length;i++) {
                for (var j=0;j<extns.length;j++) {            
                    frm.toggle_display(field_list[i]+extns[j], false);
                }
            }
        }
        for (const field_name in field_word_length_map) {
            frm.fields_dict[field_name].$input.on("keyup", function () {
                let value = $(this).val() || "";
                let words = value.trim().split(/\s+/);

                if (words.length > field_word_length_map[field_name]) {
                    frappe.msgprint(`Maximum ${field_word_length_map[field_name]} words allowed.`);
                    // Trim extra words
                    $(this).val(words.slice(0, 1).join(" "));
                }
            });            
        }        

        Object.entries(button_map).forEach(([btn, fieldname]) => {
            // Ensure the button exists in the form
            if (frm.fields_dict[btn] && frm.fields_dict[btn].input && frm.fields_dict[fieldname]) {
                frm.fields_dict[btn].input.onclick = () =>
                    handleButtonClick(frm, fieldname);
            }
        });
    }
});

frappe.realtime.on("reload_form", function (data) {
    if (cur_frm && cur_frm.doctype === data.doctype && cur_frm.doc.name === data.docname) {
        cur_frm.reload_doc();   // refresh the form data
        // or browser reload:
        // location.reload();
    }
});