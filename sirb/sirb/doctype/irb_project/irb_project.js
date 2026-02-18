var section_list = ["heq_s1","heq_s2", "heq_s3", "heq_s4", "heq_s5", "heq_s6", "heq_s7", "heq_s8", "heq_s9", "heq_s10", "heq_s11", "heq_s12", "heq_s13", "heq_s14", "heq_s15", "heq_s16", "heq_s17", "heq_s18", "heq_s19", "heq_s20", "heq_s21", "nheq_s1", "nheq_s2", "nheq_s3", "nheq_s4", "nheq_s5", "nheq_s6"]
var extns = {"_rf": "Reviewer feedback", "_prn": "Primary reviewer notes","_srn": "Secondary reviewer notes", "_sc": "Student comments", "_mf": "Mentor feedback"}
var extns_with_fc = structuredClone(extns);
extns_with_fc["_fc"] = "Field changed"

var field_word_length_map = {
    "abstract": 1
}

async function get_previous_login() {
    let res = await frappe.db.get_list("Activity Log",
        { fields: ["creation"], filters: { user: frappe.session.user, operation: "Login" }, order_by: "creation desc", limit: 2 });
    //console.log("ACTIVITY LOG ", res)
    if(res.length > 1) 
        return new Date(res[1].creation.replace(" ", "T"));
    else if (res.length === 1)
        return new Date(res[0].creation.replace(" ", "T"));
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

function get_updated_label(frm, fieldname) {
    //console.log("Passed fieldname ", fieldname)
    var field_instance = frm.get_field(fieldname);
    //console.log(field_instance)
    if (field_instance) {

        var $wrapper = $(field_instance.$wrapper);
        //field_instance.wrapper;
        //console.log("Looking in ", $wrapper)
        var $label_element = $wrapper.find('.control-label');
        
        if ($label_element.length) {
            // 4. Extract the visible text content
            var currentLabelText = $label_element.text().trim();
            
            //console.log("Current displayed label for " + fieldname + ":", currentLabelText);
            
            return currentLabelText;
        } else {
            //console.log("Label element not found for field:", fieldname);
        }
    }
    return null;
}
function field_changed_since_last_login(versions, fieldname) {
    field_changed = false;
    // console.log("Checking changes for ", fieldname)
    for (let v of versions) {
        if (v.data) {
            let version_data = JSON.parse(v.data);
            for (let change of version_data.changed) {
                // console.log(change);
                if (change[0] === fieldname) {
                    // console.log("!!")
                    field_changed = true;
                    break;
                }
            }
        }
    }
    // console.log("Returning ", field_changed)
    return field_changed
}

var get_fields_in_section = function(frm, section_fieldname) {
    let fields_in_section = [];
    let found_section = false;

    for (let field of frm.meta.fields) {
        // Start collecting when we find the target section
        if (field.fieldname === section_fieldname && field.fieldtype === 'Section Break') {
            found_section = true;
            continue;
        }

        if (found_section) {
            // Stop collecting when we hit the next Section Break
            if (field.fieldtype === 'Section Break') {
                break;
            }
            fields_in_section.push(field.fieldname);
        }
    }
    return fields_in_section;
};

function get_sections_in_tab(frm, tab_fieldname) {
    const sections = [];
    let inside_tab = false;

    frm.meta.fields.forEach(field => {
        if (field.fieldtype === 'Tab Break') {
            // console.log(field.fieldname, tab_fieldname)
            inside_tab = field.fieldname === tab_fieldname;
            return;
        }
        //console.log(inside_tab)

        if (
            inside_tab &&
            field.fieldtype === 'Section Break' &&
            field.fieldname
        ) {
            sections.push(field.fieldname);
        }
    });

    return sections;
}

function toggle_tabs(frm) {
    //console.log("IN!!")
    const type = frm.doc.project_domain;
    const tabs = [
        'animal_ethics_questionnaire_tab',
        'human_ethics_questionnaire_tab',
    ]
    //console.log(tabs)
    tabs.forEach(t => {
        //console.log(t)
        sections = get_sections_in_tab(frm, t);
        //console.log("Sections", sections)
        sections.forEach(s => frm.toggle_display(s, false));
    });

    if (type === 'All') {
        tabs.forEach(t => {
        //console.log(t)
        sections = get_sections_in_tab(frm, t);
        //console.log("Sections", sections)
        sections.forEach(s => frm.toggle_display(s, true));
    });
        return;
    }
    if (type === 'Non Human Species') {
        sections = get_sections_in_tab(frm, 'animal_ethics_questionnaire_tab');
        sections.forEach(s => frm.toggle_display(s, true));
    }
    if (type === 'Humans') {
        sections = get_sections_in_tab(frm, 'human_ethics_questionnaire_tab');
        sections.forEach(s => frm.toggle_display(s, true));
    }
}

frappe.ui.form.on("IRB Project", {

    onload_post_render(frm) {
        toggle_tabs(frm);
    },
    async onload(frm) {
        // Loop through every field in the DocType and close all review sections
        Object.keys(frm.fields_dict).forEach(fieldname => {
            // If the fieldname ends with '_addons', hide it
            if (fieldname.endsWith('_addons')) {
                frm.set_df_property(fieldname, 'hidden', 1);
            }
        });        
        frm.toggle_display('animal_ethics_questionnaire_tab', false);
        frm.toggle_display('human_ethics_questionnaire_tab', false);
        frm.toggle_display('data_ethics_questionnaire_tab', false);
        
        // setFieldReadOnly(frm, _is_student, _is_mentor, is_primary_reviewer, is_secondary_reviewer)            
        // for (var i=0;i< field_list.length;i++) {
        //     for (var extn in extns_with_fc) {            
        //         frm.toggle_display(field_list[i]+extn, false);
        //     }
        // }        
    },

    project_domain(frm) {
        // Show/hide tabs based on the project domain field
        toggle_tabs(frm);
    },

    async refresh(frm) {

        // 1. Initial Bulk Hide - Use a robust timeout
        console.log(frm.doc.num_reviewers)
        setTimeout(() => {
            if (!frm.__addons_hidden_initially) {
                Object.keys(frm.fields_dict).forEach(fieldname => {
                    if (fieldname.endsWith('_addons')) {
                        // Update metadata
                        frm.set_df_property(fieldname, 'hidden', 1);
                        // Force physical hide via jQuery
                        $(frm.fields_dict[fieldname].wrapper).hide();
                    }
                });
                frm.__addons_hidden_initially = true;
            }
        }, 600);

        // 2. The Button Listener - Direct jQuery Toggle
        $(frm.wrapper).off('click', 'button[data-fieldname^="toggle_"]');
        $(frm.wrapper).on('click', 'button[data-fieldname^="toggle_"]', function() {
            const btn_fieldname = $(this).attr('data-fieldname');
            const target_name = btn_fieldname.replace('toggle_', '') + '_addons';
            const target_field = frm.fields_dict[target_name];

            if (target_field) {
                const wrapper = $(target_field.wrapper);
                
                // Determine visibility based on physical state
                if (wrapper.is(':visible')) {
                    wrapper.hide();
                    frm.set_df_property(target_name, 'hidden', 1);
                } else {
                    wrapper.show();
                    frm.set_df_property(target_name, 'hidden', 0);
                    
                    // Optional: Smooth scroll to the revealed section
                    frappe.utils.scroll_to(target_field.wrapper, true, 30);
                }
            }
        });


        //console.log("DIRTY ", frm.is_dirty())

        // Hides the navigation buttons in the header
        frappe.dom.set_style(`
            .prev-doc, .next-doc, .menu-btn-group, .form-viewers {
                display: none !important;
            }
        `);

        // Hide the breadcrumbs
        $("#navbar-breadcrumbs").css({'visibility':'hidden'});

        // Show/hide tabs based on the project domain field
        toggle_tabs(frm);
        
        // Get the roles of the currently logged in user
        const response = await frappe.call({
            method: "sirb.api.get_irb_project_roles",
            args: { project_name: frm.doc.name, user: frappe.session.user}
        });
        let is_student = false
        let is_mentor = false
        let is_primary_reviewer = false
        let is_secondary_reviewer = false
        if (response.message) {
            //console.log("Data received:", response.message);
            is_student = response.message.is_student;
            is_mentor = response.message.is_mentor;
            is_primary_reviewer = response.message.is_primary_reviewer;
            is_secondary_reviewer = response.message.is_secondary_reviewer;
        }

        // Place a border around all data sections of the form
        for (let s of section_list) {
            section = frm.get_field(s)
            review_section = frm.get_field(s + '_addons')
            if (section && section.wrapper) {
                $(section.wrapper).css({
                    "border": "2px solid #5d5e60",
                    "border-radius": "12px",
                    "padding": "20px",
                    "margin-bottom": "20px",
                    "background-color": "#ffffff",
                    "display": "block" // Ensures the wrapper behaves as a box
                });

                // Optional: Style the header specifically to make it look integrated
                $(section.wrapper).find('.section-head').css({
                    "margin-top": "0",
                    "margin-bottom": "15px",
                    "padding-bottom": "10px",
                    "border-bottom": "1px solid #5d5e60" // Separator line under title
                });                
            }
            if (review_section && review_section.wrapper) {
                $(review_section.wrapper).css({
                    "border": "2px solid #cdcfcc",
                    "border-radius": "12px",
                    "padding": "20px",
                    "margin-bottom": "20px",
                    "background-color": "#ffffff",
                    "display": "block" // Ensures the wrapper behaves as a box
                });

                // Optional: Style the header specifically to make it look integrated
                $(review_section.wrapper).find('.section-head').css({
                    "margin-top": "0",
                    "margin-bottom": "15px",
                    "padding-bottom": "10px",
                    "border-bottom": "1px solid #cdcfcc" // Separator line under title
                });                
            }            
        };


        //console.log(frm)
        //console.log(is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer)
        //console.log("Secondary reviewer ", frm.doc.secondary_reviewer)
        if (frm.doc.secondary_reviewer != null)
            has_secondary_reviewer = true
        else
            has_secondary_reviewer = false

        // Display the role in the form intro..
        show_intro = false;
        if (is_mentor) {
            intro_role = 'faculty mentor'
            show_intro = true
        } else if (is_primary_reviewer) {
            intro_role = 'primary IRB reviewer'
            show_intro = true
        } else if (is_secondary_reviewer) {
            intro_role = 'secondary IRB reviewer'
            show_intro = true
        }
        if (show_intro)
            frm.set_intro(
                __('You are the '+intro_role+' for this IRB project.'),
                'orange', { no_dirty: true }
            );



        let roles = frappe.user_roles;
        let mentor_required = true;

        //console.log("ROLES = ", is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer)
        // console.log("HAS SECONDARY REVIEWER ", has_secondary_reviewer)

        // Now handle all the state changes and action buttons        
        if (is_student) {
            const r = await frappe.db.get_value('IRB Unit', frm.doc.irb_unit, ['mentor_required', 'num_reviewers'])
            // console.log(r.message)
            mentor_required = r.message.mentor_required
            num_reviewers = parseInt(r.message.num_reviewers)
            //console.log("MR ", mentor_required, num_reviewers);
            if (frm.doc.status === "Awaiting proposal completion by student") {
                    if (mentor_required) {
                        btn_msg = "Request Faculty Mentor Approval"
                        next_status = "Awaiting Faculty mentor approval"
                    } else if (num_reviewers == 1) {
                        btn_msg = "Request Reviewer Approval"
                        next_ststus = "Awaiting reviewer feedback to student"
                    } else { 
                        btn_msg = "Request Reviewer Approval"
                        next_status = "Awaiting primary reviewer comments"
                    }
                    // console.log(btn_msg, next_status)
                    frm.add_custom_button(btn_msg, () => {
                        frappe.call({
                            method: "sirb.api.set_project_status",  // Python method
                            args: {
                                project_id: frm.doc.name,
                                status: next_status
                            },
                            callback: function(r) {
                                if (!r.exc) {
                                    // frappe.msgprint("API executed successfully!");
                                    //CHANGE ROUTE!!!
                                    frappe.set_route("app", "irb-project", frm.doc.name)
                                }
                            }
                        });                    
                    }, "Actions");
            } else if (["Awaiting student correction for mentor feedback", "Awaiting student correction for reviewer feedback"].includes(frm.doc.status)) {
                frm.add_custom_button("Submit corrections", () => {
                    if (frm.doc.status == "Awaiting student correction for mentor feedback")
                        new_status = "Awaiting Faculty mentor approval";
                    else if (frm.doc.status == "Awaiting student correction for reviewer feedback")
                        new_status = "Awaiting reviewer feedback to student";
                    frappe.call({
                        method: "sirb.api.set_project_status",  // Python method
                        args: {
                            project_id: frm.doc.name,
                            status: new_status
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                // CHANGE ROUTE!!!
                                // frappe.msgprint("API executed successfully!");
                                frappe.set_route("app", "irb-project", frm.doc.name)
                            }
                        }
                    });                    
                }, "Actions");
            } else if (frm.doc.status === "Provisionally approved") {
                frm.add_custom_button("Submit for final approval", () => {
                    frappe.call({
                        method: "sirb.api.set_project_status",  // Python method
                        args: {
                            project_id: frm.doc.name,
                            status: "Awaiting final approval"
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                // frappe.msgprint("API executed successfully!");
                                frappe.set_route("app", "irb-project", frm.doc.name)
                            }
                        }
                    });                    
                }, "Actions");                                
            }
        } else if (is_mentor) {
            if (frm.doc.status === "Awaiting Faculty mentor approval") {
                    frm.add_custom_button("Approve for review", () => {
                        if (has_secondary_reviewer)
                            set_status = "Awaiting primary reviewer comments"
                        else
                            set_status = "Awaiting reviewer feedback to student"
                        frappe.call({
                            method: "sirb.api.set_project_status",  // Python method
                            args: {
                                project_id: frm.doc.name,
                                status: set_status
                            },
                            callback: function(r) {
                                if (!r.exc) {
                                    // frappe.msgprint("API executed successfully!");
                                    frappe.set_route("app", "irb-projects")
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
                                    frappe.set_route("app", "irb-projects")
                                }
                            }
                        });
                    }, "Actions");
    
            }
        } else if (is_primary_reviewer) {
            if (frm.doc.status ==="Awaiting reviewer feedback to student") {
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
                                frappe.set_route("app", "irb-projects")
                            }
                        }
                    });                    
                }, "Actions");
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
                                frappe.set_route("app", "irb-projects")
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
                                frappe.set_route("app", "irb-projects")
                            }
                        }
                    });
                }, "Actions");
            } else if (frm.doc.status === "Awaiting final approval") {
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
                                frappe.set_route("app", "irb-projects")
                            }
                        }
                    });
                }, "Actions");                
            } else if (frm.doc.status === "Awaiting primary reviewer comments") {
                frm.add_custom_button("Forward to secondary reviewer", () => {
                    frappe.call({
                        method: "sirb.api.set_project_status",  // Python method
                        args: {
                            project_id: frm.doc.name,
                            status: "Awaiting secondary reviewer comments"
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                // frappe.msgprint("API executed successfully!");
                                frappe.set_route("app", "irb-projects")
                            }
                        }
                    });
                }, "Actions");                
            } else if (frm.doc.status === "Provisionally approved") {
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
                                frappe.set_route("app", "irb-projects")
                            }
                        }
                    });
                }, "Actions");                
            }
        } else if (is_secondary_reviewer) {
            if (frm.doc.status ==="Awaiting secondary reviewer comments") {
                frm.add_custom_button("Forward to primary reviewer", () => {
                    frappe.call({
                        method: "sirb.api.set_project_status",  // Python method
                        args: {
                            project_id: frm.doc.name,
                            status: "Awaiting reviewer feedback to student"
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                // frappe.msgprint("API executed successfully!");
                                frappe.set_route("app", "irb-projects")
                            }
                        }
                    });                    
                }, "Actions");
            }
        }

        // Get the fields that have changed since the last login and mark them on the UI
        let last_login = await get_previous_login();
        //console.log("LAST LOGIN ", last_login)
        if(last_login) {
            let versions = await get_versions_after_login("IRB Project", frm.doc.name, last_login);
            // console.log("VERSIONS ", versions);
            //console.log(change_list_str)
            for (let section of section_list) {
                field_list = get_fields_in_section(frm, section);
                //console.log("Section ", section)
                // console.log("Field List ", field_list)
                change_list = []
                for (let version of versions) {
                    version_data = JSON.parse(version.data)
                    // console.log("VERSION DATA ", version_data)
                    for (let change of version_data["changed"]) {
                        if (change) {
                            fname = frappe.meta.get_label(frm.doctype, change[0])
                            //console.log("CHANGE0 ", change)
                            //console.log("FIELD LIST ", field_list)
                            change_in_section = field_list.some(item => item.toLowerCase() === change[0].toLowerCase());
                            //console.log("CHANGE IN SECTION ", change_in_section)
                            if (change_in_section) {
                                change_str = "'"+fname+"'  changed from '"+change[1]+"' to '"+change[2]+"'"
                                //console.log("Adding to change list ", change_str)                                
                                change_list.push(change_str)
                            }
                        }
                    }
                }
                //console.log("Change list ", change_list)
                //console.log("Change list len ", change_list.length)
                if (change_list.length !== 0 ) {
                    var change_list_str = change_list.join('<br>')
                    //console.log("Change str ", change_list_str)
                    //console.log("Setting change in ", section+"_fc")
                    //frm.set_value(section+"_fc", change_list_str, { no_dirty: true })
                    frm.set_value(section+"_fc", change_list_str, null, false)
                    //frm.get_field(section+"_fc").refresh()
                }
                var title_extns = []
                orig_label = frm.get_field(section).df.label;
                field_list = get_fields_in_section(frm, section);
                //console.log("Field list is ", field_list)
                for (let fieldname of field_list) {
                    if(field_changed_since_last_login(versions, fieldname)) {
                        // alert("field "+fieldname+" changed!!")
                        label = frm.get_field(fieldname).df.label;
                        // label = get_updated_label(frm, section);
                        
                        if (!label.toLowerCase().includes("Changed".toLowerCase()))
                            // title_extns.push("Field changed")
                            //console.log("Label updated is ", label)
                            frm.set_df_property(fieldname, "label", label + " <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>");
                            frm.get_field(fieldname).refresh()
                            // Get the field object
                            //let field = frm.get_field(fieldname);

                            //field.label_area && $(field.label_area).html(__(label + " <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>"))
                    }
                    // if (title_extns.length > 0) {
                    //     var title_ext_str = "("+title_extns.join(', ')+")"
                    //     frm.set_df_property(fieldname, "label", label + " <span style=\"background-color: yellow;\"><i>"+title_ext_str+"</i></span>");
                    // }
                }

                for (let ext in extns) {
                    section_with_ext = section + ext;
                    title_ext = []
                    // console.log(field_with_ext);
                    if(field_changed_since_last_login(versions, section_with_ext)) {
                        // alert("field "+section_with_ext+" changed!!")
                        orig_label = frm.get_field(section_with_ext).df.label;
                        updated_label = get_updated_label(frm, section_with_ext);
                        //console.log("Label is ", orig_label)
                        //console.log("Updated abel is ", updated_label)
                        //console.log(title_extns)
                        if (!(updated_label.toLowerCase().includes("changed"))) {
                            console.log("XX")
                            frm.set_df_property(section_with_ext, "label", orig_label + " <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>");
                            frm.get_field(section_with_ext).refresh()
                        }
                            //title_extns.push(extns[ext]+" added")
                            //frm.set_df_property(fieldname, "label", label + " <span style=\"background-color: yellow;\"><i>("+extns[ext]+" added) </i></span>");                                
                    }
                    // if (title_extns.length > 0) {
                    //     var title_ext_str = "("+title_extns.join(', ')+")"
                    //     console.log(title_ext_str)
                    //     frm.set_df_property(section_with_ext, "label", label + " <span style=\"background-color: yellow;\"><i>"+title_ext_str+"</i></span>");                        
                    // }
                    
                    // //console.log(title_extns)
                    //     if (title_extns.length > 0) {
                    //         var title_ext_str = "("+title_extns.join(', ')+")"
                    //         console.log("Setting title to ", title_ext_str)
                    //         //frm.set_df_property(section, "label", label + " <span style=\"background-color: yellow;\"><i>"+title_ext_str+"</i></span>");
                    //         let head = $(frm.get_field(section).wrapper).find('.section-head');
                    //         let head_contents = head.contents().filter(function() { return this.nodeType === 3; })
                    //         console.log("Head contents ", head_contents)
                    //         head_contents[0].nodeValue = orig_label + " <span style=\"background-color: yellow;\"><i>"+title_ext_str+"</i></span>";                        
                    //         //frm.refresh_field(section);
                    //     }
                }
            }
        }


        // Set the word limits for each field
        if (is_student) {
            for (const field_name in field_word_length_map) {
                //console.log(field_name);
                //console.log(frm.fields_dict[field_name]);
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
        }

    }
});

frappe.realtime.on("reload_form", function (data) {
    if (cur_frm && cur_frm.doctype === data.doctype && cur_frm.doc.name === data.docname) {
        cur_frm.reload_doc();   // refresh the form data
        // or browser reload:
        // location.reload();
    }
});

        // Setup the actions for each button appropriately
        // Object.entries(button_map).forEach(([btn, fieldname_list]) => {
        //     // Ensure the button exists in the form
        //     if (frm.fields_dict[btn] && frm.fields_dict[btn].input && frm.fields_dict[fieldname_list[1]]) {
        //         frm.fields_dict[btn].input.onclick = () =>
        //             handleButtonClick(frm, fieldname_list, is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer);
        //     }
        // });
// var button_map = {}
// // for (var i=0;i< field_list.length;i++) {
// //     for (var extn in extns_with_fc) {
// //         button_map[field_list[i]+extn+"_button"] = [field_list[i], field_list[i]+extn];
// //     }
// // }
// for (var i=0;i< section_list.length;i++) {
//     for (var extn in extns_with_fc) {
//         button_map[section_list[i]+extn+"_button"] = [section_list[i], section_list[i]+extn];
//     }
// }
// console.log(button_map);

//var field_list = ["abstract", "consent_form_attachment"];

// function setFieldReadOnly(frm, is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer) {
//     console.log("roles", is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer)
//     for (var i=0;i< section_list.length;i++) {
//         for (var extn in extns_with_fc) { 
//             //frm.toggle_display(section_list[i]+extn, false);
//             // frm.set_df_property(section_list[i]+extn, "hidden", 0);
//             const field = frm.fields_dict[section_list[i]+extn];
//             if (is_student) {
//                 if (extn == "_sc")
//                     frm.set_df_property(section_list[i]+extn, "read_only", 0);
//                     //frm.toggle_enable(section_list[i]+extn, true);
//                 else {
//                     frm.set_df_property(section_list[i]+extn, "read_only", 1);
//                     //frm.toggle_enable(section_list[i]+extn, false);
//                     //frm.set_df_property(section_list[i]+extn, "read_only", 1);
//                     // console.log(section_list[i]+extn);
//                     // field.df.read_only = 1;
//                     // field.df.hidden = 0;
//                     // field.disp_status = "Read";
//                     // frm.get_field(section_list[i]+extn).$wrapper.attr('style', 'display: block !important;');

//                     // brute-force UI fix
//                     //field.$wrapper.show();                    
//                     //frm.set_df_property(section_list[i]+extn, "disabled", 1);
//                     //frm.set_df_property(section_list[i]+extn, "display", 1);
//                 }
//                 frm.refresh_field(section_list[i]+extn);
//             }
//             if (is_mentor) {
//                 if (extn == "_mf")
//                     frm.set_df_property(section_list[i]+extn, "read_only", 0);
//                 else
//                     frm.set_df_property(section_list[i]+extn, "read_only", 1);
//             }
//             if (is_primary_reviewer){
//                 if (["_prn", "_rc"].includes(extn))
//                     frm.set_df_property(section_list[i]+extn, "read_only", 0);
//                 else
//                     frm.set_df_property(section_list[i]+extn, "read_only", 1);
//             }
//             if (is_secondary_reviewer) {
//                 if (extn == "_srn")
//                     frm.set_df_property(section_list[i]+extn, "read_only", 0);
//                 else
//                     frm.set_df_property(section_list[i]+extn, "read_only", 1);
//             }            
//         }
//     }
// }


// function setFieldVisibility(frm, is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer) {
//     console.log("roles", is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer)
//     for (var i=0;i< section_list.length;i++) {
//         for (var extn in extns_with_fc) { 
//             //frm.toggle_display(section_list[i]+extn, false);
//             // frm.set_df_property(section_list[i]+extn, "hidden", 0);
//             const field = frm.fields_dict[section_list[i]+extn];
//             if (is_student) {
//                 if (["_prn", "_srn","_fc"].includes(extn)) {
//                     // console.log("toggling off display for ", section_list[i]+extn);
//                     frm.toggle_display(section_list[i]+extn+"_button", false);
//                     frm.toggle_display(section_list[i]+extn, false);
//                 }
//                 else {
//                     frm.get_field(section_list[i]+extn).$wrapper.attr('style', 'display: block !important;');
//                     frm.toggle_display(section_list[i]+extn, true);
//                 }
//                 frm.refresh_field(section_list[i]+extn);
//             }
//             if (is_mentor) {
//                 if (extn == "_mf")
//                     frm.set_df_property(section_list[i]+extn, "read_only", 0);
//                 else
//                     frm.set_df_property(section_list[i]+extn, "read_only", 1);
//                 if (["_prn", "_srn"].includes(extn)) {
//                     // console.log("toggling off display for ", section_list[i]+extn);
//                     frm.toggle_display(section_list[i]+extn+"_button", false);
//                     frm.toggle_display(section_list[i]+extn, false);
//                 } else {
//                     frm.get_field(section_list[i]+extn).$wrapper.attr('style', 'display: block !important;');
//                     frm.toggle_display(section_list[i]+extn, true);
//                 }
//             }
//             if (is_primary_reviewer){
//                 frm.get_field(section_list[i]+extn).$wrapper.attr('style', 'display: block !important;');
//                 frm.toggle_display(section_list[i]+extn, true);
//             }
//             if (is_secondary_reviewer) {
//                 frm.get_field(section_list[i]+extn).$wrapper.attr('style', 'display: block !important;');
//                 frm.toggle_display(section_list[i]+extn, true);                
//             }            
//         }
//     }
// }

// function handleButtonClick(frm, fieldname_list, is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer) {
//     console.log(fieldname_list)
    
//     if (is_student) {
//         allowed_fields = ["_rf", "_mf", "_sc"]
//         let matches = allowed_fields.some(ending => fieldname_list[1].endsWith(ending));
//         if (!matches)
//             return
//     }
//     if (is_mentor) {
//         allowed_fields = ["_rf", "_mf", "_sc", "_fc"]
//         let matches = allowed_fields.some(ending => fieldname_list[1].endsWith(ending));
//         if (!matches)
//             return
//     }
//     if (is_primary_reviewer) {
//         allowed_fields = ["_rf", "_mf", "_sc", "_prn", "_srn", "_fc"]
//         let matches = allowed_fields.some(ending => fieldname_list[1].endsWith(ending));
//         if (!matches)
//             return        
//     }
//     if (is_secondary_reviewer) {
//         allowed_fields = ["_rf", "_mf", "_sc", "_prn", "_srn", "_fc"]
//         let matches = allowed_fields.some(ending => fieldname_list[1].endsWith(ending));
//         if (!matches)
//             return
//     }    
//     let st = Boolean(frm.get_field(fieldname_list[1]).df.hidden);    
//     if (!(fieldname_list[1].toLowerCase().includes("_fc"))) {
//         // Some field other than field changes so close all and only toggle the one clicked
//         for (var extn in extns) {
//             frm.toggle_display(fieldname_list[0]+extn, false);
//         }
//     }
//     //console.log(fieldname_list[1]);
//     //console.log(st);
//     //frm.toggle_display(fieldname_list[1], st);
// }
