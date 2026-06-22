var section_list = ["heq_s1","heq_s2", "heq_s3", "heq_s4", "heq_s5", "heq_s6", "heq_s7", "heq_s8", "heq_s9", "heq_s10", "heq_s11", "heq_s12", "heq_s13", "heq_s14", "heq_s15", "heq_s16", "heq_s17", "heq_s18", "heq_s19", "heq_s20", "nheq_s0","nheq_s1", "nheq_s2", "nheq_s3", "nheq_s4", "nheq_s5", "nheq_s6", "nheq_s7", "nheq_s8", "nheq_s9","uploads_s1"]
var extns = {"_rf": "Reviewer feedback", "_prn": "Primary reviewer notes","_srn": "Secondary reviewer notes", "_sc": "Student comments", "_mf": "Mentor feedback"}
var extns_with_fc = structuredClone(extns);
extns_with_fc["_fc"] = "Field changed"

var field_word_length_map = {
    "abstract": 500,
    "state_your_project_question":  200,
    "nheq_project_question": 200,
    "project_context": 10,
    "nheq_project_context": 10,
    "project_subjects": 200,
    "consent_type_and_explanation": 600,
    "consent_text_for_minors": 600,
    "recording_consent": 600,
    "sensitive_population_field": 100,
    "approaching_participants" : 300,
    "data_collection_methods_and_locations" : 600,
    "participant_risks_and_mitigation":  350,
    "student_risks_and_mitigation": 350,
    "trust_of_participants": 300,
    "consent_text_for_participation": 600,
    "interventions" : 300,
    "need_for_such_data": 400,
    "consent_for_photos": 400,
    "photos_confidentiality":  200,
    "other_data":  200
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
async function get_versions_after_status_change(doctype, docname, status) {
    console.log("Checking versions after ", status)
    let versions = await frappe.db.get_list("Version",
        {
            fields: ["data", "modified"],
            filters: [
                ["docname", "=", docname],
                ["ref_doctype", "=", doctype]
            ],
            order_by: "modified desc",
            limit_page_length: 9999
        });
    let changed_versions = []
    for (let version of versions) {
        found_needed_status_change = false;
        if (version.data) {
            let version_data = JSON.parse(version.data);
            for (let change_info of version_data.changed) {
                if (change_info && change_info[0] === "status" && change_info[2] === status) {
                        // console.log("FOUND NEEDED STATUS CHANGE! ", change_info)
                        found_needed_status_change = true;
                        break;
                }
            }
            if (!found_needed_status_change)
                changed_versions.push(version)
            else
                break;
        }
    }
    if (found_needed_status_change) {
        console.log("CHANGES ", changed_versions);
        return changed_versions;
    } else
        console.log("NO CHANGES FOUND!")
        return []

}
function get_field_changes_from_version_list(versions, fieldname) {
    let changes = []
    for (let version of versions) {
        let version_data = JSON.parse(version.data);
        for (let change_info of version_data.changed) {
            if (change_info && change_info[0] === fieldname) {
                change = {}
                change["date"] = version.modified
                change["old_value"] = change_info[1]
                change["new_value"] = change_info[2]
                changes.push(change)
            }
        }
    }
    // console.log("FOUND NEEDED FIELD CHANGE! ", changes)
    return changes
}
function clear_all_field_changes(frm) {
    console.log("TRYING TO CLEAR!")
    Object.keys(frm.fields_dict).forEach(fieldname => {
        let field = frm.get_field(fieldname);
        if (!field || !field.$wrapper) return;
        let $label = field.$wrapper.find('.control-label');
        // Remove any span whose text contains "(Field Changed)"
        $label.find('span').each(function() {
            if ($(this).text().includes('(Field Changed)')) {
                console.log("REMOVING!")
                $(this).remove();
            }
        });
    });
}

async function update_field_changes(frm, doctype, docname, status) {
    console.log("CHECKING FIELD UPDATES AFTER ", status, " !!")
    let changed_versions = await get_versions_after_status_change(doctype, docname, status)
    if (changed_versions.length > 0) {
        console.log("FOUND CHANGED VERSIONS!")
        for (let section of section_list) {
            field_changes_str = '';
            field_list = get_fields_in_section(frm, section);
            for (let field of field_list) {
                //console.log(field);
                field_changes = get_field_changes_from_version_list(changed_versions, field)
                if (field_changes.length > 0) {
                    console.log(field, " changed so updating field changes label!")
                    for (let field_change of field_changes) {
                        field_changes_str += field + " changed from \"" + field_change.old_value + "\" to \"<b>" + field_change.new_value + "</b>\" on " + field_change.date + "\n"
                    }
                    updated_label = get_updated_label(frm, field);
                    if (!(updated_label.toLowerCase().includes("changed"))) {
                        let orig_label = frm.get_field(field).df.label;
                        if (field && field.$wrapper) {
                            let $label = field.$wrapper.find('.control-label');
                            if ($label.length) {
                                // Keep the original text inside the label, append the marker as HTML
                                $label.html(orig_label + ' <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>');
                            }
                        }                        
                        // frm.set_df_property(field, "label", orig_label + " <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>");
                    }                    
                }
            }
            if (field_changes_str !== '') {
                frm.set_value(section+"_fc", field_changes_str, null, false);
            }
            let section_ext_changed = false;
            for (let ext in extns) {
                if (ext === "_fc")
                    continue;
                section_with_ext = section + ext;
                title_ext = [];
                field_changes = get_field_changes_from_version_list(changed_versions, section_with_ext);
                //console.log("checking extension ", section_with_ext)
                if (field_changes.length > 0) {
                    console.log(section_with_ext, " changed so updating field changes label!")
                    section_ext_changed = true;
                    updated_label = get_updated_label(frm, section_with_ext);
                    if (!(updated_label.toLowerCase().includes("changed"))) {
                        let orig_label = frm.get_field(section_with_ext).df.label;
                        //frm.set_df_property(section_with_ext, "label", orig_label + " <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>");
                        if (section_with_ext && section_with_ext.$wrapper) {
                            let $label = section_with_ext.$wrapper.find('.control-label');
                            if ($label.length) {
                                // Keep the original text inside the label, append the marker as HTML
                                $label.html(orig_label + ' <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>');
                            }
                        }                        
                    }
                }
            }
            if (section_ext_changed) {
                console.log("UPDATEING TOGGLE BUTTON LABEL!")
                orig_label = frm.get_field("toggle_"+section).df.label;
                if (!orig_label.toLowerCase().includes("changed")) {
                    frm.set_df_property("toggle_"+section, "label", orig_label + " <span style=\"background-color: yellow;\"><i> (Review Section Changed) </i></span>");
                    frm.get_field(section_with_ext).refresh()
                }
            }
        }
    }
}

async function get_versions_after_login(doctype, docname, prev_login_time) {
    let prev_login_str = prev_login_time.getFullYear() + '-' +
                            String(prev_login_time.getMonth() + 1).padStart(2, '0') + '-' +
                            String(prev_login_time.getDate()).padStart(2, '0') + ' ' +
                            String(prev_login_time.getHours()).padStart(2, '0') + ':' +
                            String(prev_login_time.getMinutes()).padStart(2, '0') + ':' +
                            String(prev_login_time.getSeconds()).padStart(2, '0');
    // console.log("Prev login str is ", prev_login_str)
    let versions = await frappe.db.get_list("Version",
        {
            fields: ["data", "modified"],
            filters: [
                ["docname", "=", docname],
                ["ref_doctype", "=", doctype],
                ["modified", ">", prev_login_str]
            ],
            order_by: "modified desc",
            limit_page_length: 9999
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

function handle_toggle_all_comment_sections(frm){
    const allowed_open_all_comment_section_roles = ['Administrator', 'System Manager', "Primary IRB Reviewer", "Secondary IRB Reviewer"];
    const sectionsToToggle = [];
    // console.log("IN!")
    frm.remove_custom_button(__('Toggle All Sections'));
    //let allFieldnamesToToggle = [];
    applicable_sections = []
    if (["Non Human Species", "BOTH Humans AND Non Humans"].includes(frm.doc.project_domain))
        applicable_sections.push(...get_sections_in_tab(frm, "animal_ethics_questionnaire_tab"));
    if (["Humans", "BOTH Humans AND Non Humans"].includes(frm.doc.project_domain))
        applicable_sections.push(...get_sections_in_tab(frm, "human_ethics_questionnaire_tab"));
    // console.log(applicable_sections);
    for (let fieldname of applicable_sections) {
        // console.log(fieldname)
        // console.log(fieldname.endsWith('_addons'))
        if (fieldname.endsWith('_addons')) {
            //console.log(fieldname)
            base_section = fieldname.slice(0, -7); // -7 is the len("_addons")
            //console.log(base_section)
            base_section_field = frm.get_field(base_section);
            //console.log(base_section)
            //console.log(base_section_field.df.hidden)
            //console.log(base_section_field.wrapper)
            //console.log(base_section_field.df.hidden === 0, base_section_field.wrapper.is(":visible"))
            //console.log(base_section_field.df)
            //console.log(base_section_field.wrapper)
            let wrapper = $(base_section_field.wrapper);
            //console.log(base_section_field.wrapper)
            if (base_section_field && ( wrapper.css('display') === 'block'))
                sectionsToToggle.push(fieldname);
            //allFieldnamesToToggle.push(fieldname);
        }
    }
    //console.log(sectionsToToggle);
    if (frappe.user_roles.some(role => allowed_open_all_comment_section_roles.includes(role))) {
        if (["Humans", "Non Human Species", "BOTH Humans AND Non Humans"].includes(frm.doc.project_domain)) {
            frm.add_custom_button(__('Toggle All Sections'), () => {
                frm._toggleAddonsState = !frm._toggleAddonsState;
                const show = frm._toggleAddonsState;   // true = show sections, false = hide
                // Apply hidden property to all collected fields
                //console.log(show)
                sectionsToToggle.forEach(fieldname => {
                    const wrapper = $(frm.fields_dict[fieldname].wrapper);;
                    if (show)
                        wrapper.show();
                    else
                        wrapper.hide();
                    frm.set_df_property(fieldname, 'hidden', !show);
                });
            })                
        }
    }
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

    if (type === 'BOTH Humans AND Non Humans') {
        tabs.forEach(t => {
            //console.log(t)
            sections = get_sections_in_tab(frm, t);
            //console.log("Sections", sections)
            sections.forEach(s => frm.toggle_display(s, true));
        });
    }
    if (type === 'Non Human Species') {
        sections = get_sections_in_tab(frm, 'animal_ethics_questionnaire_tab');
        sections.forEach(s => frm.toggle_display(s, true));
    }
    if (type === 'Humans') {
        sections = get_sections_in_tab(frm, 'human_ethics_questionnaire_tab');
        sections.forEach(s => frm.toggle_display(s, true));
    }
    handle_toggle_all_comment_sections(frm);
}

async function get_logged_in_role(frm) {
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
    return [is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer]   
}

async function toggle_save_button(frm) {
    // Hide the save button based on state
    // console.log(typeof get_logged_in_role);
    // const result = await get_logged_in_role(frm);
    // console.log(result); // Should be an array
    // console.log(Array.isArray(result));
    const [is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer] = await get_logged_in_role(frm);
    let disable_button = false;
    if (is_student && !["Awaiting proposal completion by student",
        "Awaiting student correction for mentor feedback",
        "Awaiting student correction for reviewer feedback",
        "Provisionally approved", "Approved"].includes(frm.doc.status)) {
        disable_button = true;
    }
    if (is_mentor && !["Awaiting Faculty mentor approval", "Approved"].includes(frm.doc.status)) {
        disable_button = true;
    }
    if (is_primary_reviewer && !["Awaiting primary reviewer comments to secondary reviewer",
        "Awaiting reviewer feedback to student",
        "Awaiting final approval", "Approved"].includes(frm.doc.status)) {
        disable_button = true;
    }
    if (is_secondary_reviewer && !["Awaiting secondary reviewer comments to primary reviewer", "Approved"].includes(frm.doc.status)) {
        disable_button = true;
    }

    if (disable_button) {
        // Hide the primary save button
        frm.page.set_primary_action(null);
        frm.save_button.hide();
        // Optionally disable keyboard save (Ctrl+S)
        disable_keyboard_save(true);
    }
    else {
        // Restore the default save button (if it was removed)
        // Note: You might need to re-create it. Frappe's default action is 'Save'.
        if (!frm.page.btn_primary || !frm.page.btn_primary.is(':visible')) {
            frm.page.set_primary_action(__('Save'), () => frm.save(), null, 'btn-primary');
        }
        frm.save_button.show();
        disable_keyboard_save(false);
    }
}

let save_keyboard_disabled = false;

function disable_keyboard_save(disable) {
    if (disable === save_keyboard_disabled) return;
    if (disable) {
        $(window).on('keydown.saveblock', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.which === 83) {
                frappe.msgprint(__('The current project status does not allow you to modify the form.'));
                e.preventDefault();
                return false;
            }
        });
    } else {
        $(window).off('keydown.saveblock');
    }
    save_keyboard_disabled = disable;
};
async function update_status(frm, status) {
    frappe.call({
        method: "sirb.api.set_project_status",  // Python method
        args: {
            project_id: frm.doc.name,
            status: status
        },
        callback: function(r) {
            if (!r.exc) {
                //frappe.msgprint("API executed successfully!");
                frm.reload_doc();
                //frappe.set_route("app", "irb-projects")
            }
        }
    });    
}
async function process_status_change_button(frm, status) {
    if (frm.is_dirty()) {    
        frappe.show_alert({ message: __('Saving changes...'), indicator: 'green' });
        frm.save()
            .then(() => {
                // The 'then' block runs only if both client and server validations pass
                console.log("UPDATING STATUS!")
                update_status(frm, status);
            })
            .catch((err) => {
                // If validation fails, the save is aborted and the error is shown automatically
                console.error("Save failed:", err);
                frappe.msgprint(__('Please correct the errors before proceeding.'));
            });
    } else {
        update_status(frm, status);
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
    research_type(frm) {
        handle_toggle_all_comment_sections(frm);
    },
    minor_participants(frm) {
        handle_toggle_all_comment_sections(frm);
    },
    will_data_be_gathered_through_digital_means(frm) {
        handle_toggle_all_comment_sections(frm);
    },
    status: function(frm) {
        // Whenever the status field changes, re-evaluate
        toggle_save_button(frm);
    },
    async refresh(frm) {
        // 1. Initial Bulk Hide - Use a robust timeout
        // console.log(frm.doc.num_reviewers)
        // Store a reference to the save button for later use
        if (!frm.save_button) {
            frm.save_button = frm.page.btn_primary;
        }
        toggle_save_button(frm);
        // Get the roles of the currently logged in user
        const [is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer] = await get_logged_in_role(frm);
        if (is_student && ["Humans","Non Human Species", "BOTH Humans AND Non Humans"].includes(frm.doc.project_domain) && frm.doc.status !== "Awaiting proposal completion by student")
            frm.set_df_property('project_domain', 'read_only', 1);
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
                    if (is_student) {
                        let show_talk_to_reviewer = false;
                        if (["Awaiting student correction for reviewer feedback"].includes(frm.doc.status)) 
                            show_talk_to_reviewer = true;
                        else
                            show_talk_to_reviewer = false;
                        // console.log("talk ", show_talk_to_reviewer)
                        for (let s of section_list) {
                            fname = s+"_sc";
                            // console.log(fname);
                            if (!show_talk_to_reviewer)
                                frm.set_df_property(fname, 'hidden', 1);
                            else
                                frm.set_df_property(fname, 'hidden', 0);
                        }
                    }
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
        if (frm.doc.__islocal) return; // Don't run on unsaved docs

        if (frm._toggleAddonsState === undefined) {
            frm._toggleAddonsState = false;   // false = sections are visible
        }

        //console.log(sectionsToToggle);
        // sectionsToToggle.forEach(section => {
        //     allFieldnamesToToggle.push(...get_fields_in_section(frm, section));
        // });
        // Remove duplicates (if any field belongs to more than one section – shouldn’t happen)
        //allFieldnamesToToggle = [...new Set(allFieldnamesToToggle)];        
        //console.log(sectionsToToggle);

        if (!frm.doc.research_type)
            frm.set_value('research_type', '-- Select --');
        if (!frm.doc.project_domain)
            frm.set_value('project_domain', '-- Select --');
        if (!frm.doc.consent_for_people_interaction)
            frm.set_value('consent_for_people_interaction', '-- Select --');
        if (!frm.doc.minor_participants)
            frm.set_value('minor_participants', '-- Select --'); 
        if (!frm.doc.will_data_be_gathered_through_digital_means)
            frm.set_value('will_data_be_gathered_through_digital_means', '-- Select --');
        if (!frm.doc.manipulative_experiments_select)
            frm.set_value('manipulative_experiments_select', '-- Select --');         

        // SHOW FIELD UPDATES
        clear_all_field_changes(frm);
        if (frm.doc.status == "Awaiting student correction for mentor feedback") {
            // SHOW STUDENT THE UPDATES FROM MENTOR
            await update_field_changes(frm, "IRB Project", frm.doc.name, "Awaiting Faculty mentor approval");
        }
        else if (frm.doc.status == "Awaiting student correction for reviewer feedback") {
            // SHOW STUDENT THE UPDATES FROM REVIEWER
            await update_field_changes(frm, "IRB Project", frm.doc.name, "Awaiting reviewer feedback to student");
        }
        else if (frm.doc.status === "Awaiting Faculty mentor approval") {
            // SHOW MENTOR THE UPDATES FROM STUDENT
            await update_field_changes(frm, "IRB Project", frm.doc.name,"Awaiting student correction for mentor feedback");
        }
        else if (frm.doc.status ==="Awaiting reviewer feedback to student") {
            // SHOW REVIEWER THE UPDATES FROM STUDENT
            await update_field_changes(frm, "IRB Project", frm.doc.name,"Awaiting student correction for reviewer feedback")
        }
        frappe.call({
            method: "sirb.api.get_project_students",
            args: { project_name: frm.doc.name },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    // Create a simple, clean table
                    let html = `
                        <table class="table table-bordered table-condensed" style="background-color: #f8f9fa;">
                            <thead>
                                <tr>
                                    <th>Student Name</th>
                                    <th>Student Email</th>
                                    <th>Student ID</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;

                    r.message.forEach(row => {
                        html += `
                            <tr>
                                <td>${row.full_name}</td>
                                <td>${row.user_email || ''}</td>
                                <td>${row.student_id || ''}</td>
                            </tr>
                        `;
                    });

                    html += `</tbody></table>`;
                    
                    // Set the HTML into the field
                    frm.set_df_property('student_information', 'options', html);
                } else {
                    frm.set_df_property('student_information', 'options', '<p class="text-muted">No students assigned to this project.</p>');
                }
            }
        });


        //console.log(frm)
        //console.log(is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer)
        console.log("Secondary reviewer ", frm.doc.secondary_reviewer)
        if (frm.doc.secondary_reviewer != null && frm.doc.secondary_reviewer != "")
            has_secondary_reviewer = true
        else
            has_secondary_reviewer = false
        console.log("has_secondary_reviewer ", has_secondary_reviewer)

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

        // console.log("ROLES = ", is_student, is_mentor, is_primary_reviewer, is_secondary_reviewer)
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
                        next_status = "Awaiting primary reviewer comments to secondary reviewer"
                    }
                    
                    // console.log(btn_msg, next_status)
                    frm.add_custom_button(btn_msg, () => {
                        process_status_change_button(frm, next_status, true);
                        // frappe.call({
                        //     method: "sirb.api.set_project_status",  // Python method
                        //     args: {
                        //         project_id: frm.doc.name,
                        //         status: next_status
                        //     },
                        //     callback: function(r) {
                        //         if (!r.exc) {
                        //             // frappe.msgprint("API executed successfully!");
                        //             frm.reload_doc();
                        //             frappe.set_route("app", "irb-project", frm.doc.name)
                        //         }
                        //     }
                        // });                    
                    }, "Actions");
            } else if (["Awaiting student correction for mentor feedback", "Awaiting student correction for reviewer feedback"].includes(frm.doc.status)) {
                if (frm.doc.status == "Awaiting student correction for mentor feedback") {
                    new_status = "Awaiting Faculty mentor approval";
                    // UPDATE THE FIELD CHANGES LABELS
                }
                else if (frm.doc.status == "Awaiting student correction for reviewer feedback") {
                    new_status = "Awaiting reviewer feedback to student";
                    // UPDATE THE FIELD CHANGES LABELS
                }
                frm.add_custom_button("Submit corrections", () => {
                    process_status_change_button(frm, new_status, true);
                }, "Actions");
                // frm.add_custom_button("Submit corrections", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: new_status
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-project", frm.doc.name)
                //             }
                //         }
                //     });                    
                // }, "Actions");
            } else if (frm.doc.status === "Provisionally approved") {
                frm.add_custom_button("Submit for final approval", () => {
                    process_status_change_button(frm, "Awaiting final approval", true);
                }, "Actions");                
                // frm.add_custom_button("Submit for final approval", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: "Awaiting final approval"
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-project", frm.doc.name)
                //             }
                //         }
                //     });                    
                // }, "Actions");                                
            }
        } else if (is_mentor) {
            if (frm.doc.status === "Awaiting Faculty mentor approval") {
                console.log("has_secondary_reviewer ", has_secondary_reviewer)
                if (has_secondary_reviewer)
                    set_status = "Awaiting primary reviewer comments to secondary reviewer"
                else
                    set_status = "Awaiting reviewer feedback to student"             
                frm.add_custom_button("Approve for review", () => {
                    process_status_change_button(frm, set_status, false);
                }, "Actions");
                frm.add_custom_button("Request corrections from student", () => {
                    process_status_change_button(frm, "Awaiting student correction for mentor feedback", false);
                }, "Actions");
                
                // frm.add_custom_button("Approve for review", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: set_status
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-projects")
                //             }
                //         }
                //     });                    
                // }, "Actions");
                // frm.add_custom_button("Request corrections from student", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: "Awaiting student correction for mentor feedback"
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-projects")
                //             }
                //         }
                //     });
                // }, "Actions");
            }
        } else if (is_primary_reviewer) {
            if (frm.doc.status ==="Awaiting reviewer feedback to student") {
                frm.add_custom_button("Request corrections from student", () => {
                    process_status_change_button(frm, "Awaiting student correction for reviewer feedback", false);
                }, "Actions");
                frm.add_custom_button("Grant FINAL approval", () => {
                    process_status_change_button(frm, "Approved", false);
                }, "Actions");
                frm.add_custom_button("Grant PROVISIONAL approval", () => {
                    process_status_change_button(frm, "Provisionally approved", false);
                }, "Actions");
                
                // frm.add_custom_button("Request corrections from student", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: "Awaiting student correction for reviewer feedback"
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-projects")
                //             }
                //         }
                //     });
                // }, "Actions");
                // frm.add_custom_button("Grant FINAL approval", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: "Approved"
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-projects")
                //             }
                //         }
                //     });
                // }, "Actions");
                // frm.add_custom_button("Grant PROVISIONAL approval", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: "Provisionally approved"
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-projects")
                //             }
                //         }
                //     });
                // }, "Actions");
            } else if (frm.doc.status === "Awaiting final approval") {
                frm.add_custom_button("Grant FINAL approval", () => {
                    process_status_change_button(frm, "Approved", false);
                }, "Actions");                
                // frm.add_custom_button("Grant FINAL approval", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: "Approved"
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-projects")
                //             }
                //         }
                //     });
                // }, "Actions");                
            } else if (frm.doc.status === "Awaiting primary reviewer comments to secondary reviewer") {
                frm.add_custom_button("Forward to secondary reviewer", () => {
                    process_status_change_button(frm, "Awaiting secondary reviewer comments to primary reviewer", false);
                }, "Actions");                
                // frm.add_custom_button("Forward to secondary reviewer", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: "Awaiting secondary reviewer comments"
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-projects")
                //             }
                //         }
                //     });
                // }, "Actions");                
            } else if (frm.doc.status === "Provisionally approved") {
                frm.add_custom_button("Grant FINAL approval", () => {
                    process_status_change_button(frm, "Approved", false);
                }, "Actions");                
                // frm.add_custom_button("Grant FINAL approval", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: "Approved"
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-projects")
                //             }
                //         }
                //     });
                // }, "Actions");                
            }
        } else if (is_secondary_reviewer) {
            if (frm.doc.status ==="Awaiting secondary reviewer comments to primary reviewer") {
                frm.add_custom_button("Forward to primary reviewer", () => {
                    process_status_change_button(frm, "Awaiting reviewer feedback to student", false);
                }, "Actions");
                // frm.add_custom_button("Forward to primary reviewer", () => {
                //     frappe.call({
                //         method: "sirb.api.set_project_status",  // Python method
                //         args: {
                //             project_id: frm.doc.name,
                //             status: "Awaiting reviewer feedback to student"
                //         },
                //         callback: function(r) {
                //             if (!r.exc) {
                //                 // frappe.msgprint("API executed successfully!");
                //                 frm.reload_doc();
                //                 frappe.set_route("app", "irb-projects")
                //             }
                //         }
                //     });                    
                // }, "Actions");
            }
        }

        // // Get the fields that have changed since the last login and mark them on the UI
        // let last_login = await get_previous_login();
        // //console.log("LAST LOGIN ", last_login)
        // if(last_login) {
        //     let versions = await get_versions_after_login("IRB Project", frm.doc.name, last_login);
        //     if (versions && versions.length > 0) {
        //         //console.log("versions ", versions)
        //         //last_version = versions[versions.length - 1]
        //         //console.log("Version 0 is ", versions[0].data)
        //         //console.log("VERSIONS ", versions);
        //         //console.log(change_list_str)
        //         for (let section of section_list) {
        //             field_list = get_fields_in_section(frm, section);
        //             //console.log("Section ", section)
        //             // console.log("Field List ", field_list)
        //             fields_modifications_added = []
        //             change_list = []
        //             for (let version of versions) {
        //                 //console.log("version is ", version)                        
        //                 version_data = JSON.parse(version.data)
        //                 //console.log("VERSION DATA ", version_data)
        //                 for (let change of version_data["changed"]) {
        //                     if (change) {
        //                         fname = frappe.meta.get_label(frm.doctype, change[0])
        //                         //console.log("CHANGED ", change)
        //                         //console.log("FIELD LIST ", field_list)
        //                         change_in_section = field_list.some(item => item.toLowerCase() === change[0].toLowerCase());
        //                         //console.log("CHANGE IN SECTION ", change_in_section)
        //                         if (change_in_section) {
        //                             //console.log(change)
        //                             //for (i=0;i<field_list.length;i++)
        //                             if (change[1] != "" && change[1] != null && !fields_modifications_added.includes(change[0])) {
        //                                 fields_modifications_added.push(change[0])
        //                                 fieldname = change[0]
        //                                 //console.log(fieldname, " changed!")
        //                                 label = frm.get_field(fieldname).df.label;
        //                                 // label = get_updated_label(frm, section);
        //                                 if (!label.toLowerCase().includes("Changed".toLowerCase()) && !(fieldname.startsWith("toggle_")))
        //                                     // title_extns.push("Field changed")
        //                                     //console.log("Label updated is ", label)
        //                                     frm.set_df_property(fieldname, "label", label + " <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>");
        //                                     frm.get_field(fieldname).refresh()
        //                                 //console.log("ADDING!")
        //                                 change_str = "'"+fname+"'  changed from '"+change[1]+"' to '<b>"+change[2]+"</b>'"
        //                                 //console.log("Adding to change list ", change_str)                                
        //                                 change_list.push(change_str)
        //                             }
        //                         }
        //                     }
        //                 }
        //                 //}
        //                 //console.log("Change list ", change_list)
        //                 //console.log("Change list len ", change_list.length)
        //                 if (change_list.length !== 0 ) {
        //                     var change_list_str = change_list.join('<br>')
        //                     //console.log("Change str ", change_list_str)
        //                     //console.log("Setting change in ", section+"_fc")
        //                     //frm.set_value(section+"_fc", change_list_str, { no_dirty: true })
        //                     frm.set_value(section+"_fc", change_list_str, null, false)
        //                     //frm.get_field(section+"_fc").refresh()
        //                 }
        //                 var title_extns = []
        //                 // orig_label = frm.get_field(section).df.label;
        //                 // field_list = get_fields_in_section(frm, section);
        //                 // //console.log("Field list is ", field_list)
        //                 // for (let fieldname of field_list) {
        //                 //     if(field_changed_since_last_login(versions, fieldname)) {
        //                 //         // alert("field "+fieldname+" changed!!")
        //                 //         if (fieldname.startsWith("toggle_"))
        //                 //             continue
        //                 //         label = frm.get_field(fieldname).df.label;
        //                 //         // label = get_updated_label(frm, section);
        //                 //         if (!label.toLowerCase().includes("Changed".toLowerCase()))
        //                 //             // title_extns.push("Field changed")
        //                 //             //console.log("Label updated is ", label)
        //                 //             frm.set_df_property(fieldname, "label", label + " <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>");
        //                 //             frm.get_field(fieldname).refresh()
        //                 //             // Get the field object
        //                 //             //let field = frm.get_field(fieldname);

        //                 //             //field.label_area && $(field.label_area).html(__(label + " <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>"))
        //                 //     }
        //                     // if (title_extns.length > 0) {
        //                     //     var title_ext_str = "("+title_extns.join(', ')+")"
        //                     //     frm.set_df_property(fieldname, "label", label + " <span style=\"background-color: yellow;\"><i>"+title_ext_str+"</i></span>");
        //                     // }
        //                 //}
        //                 let section_ext_changed = false
        //                 for (let ext in extns) {
        //                     section_with_ext = section + ext;
        //                     title_ext = []
        //                     // console.log(field_with_ext);
        //                     if(field_changed_since_last_login(versions, section_with_ext)) {
        //                         section_ext_changed = true
        //                         // alert("field "+section_with_ext+" changed!!")
        //                         orig_label = frm.get_field(section_with_ext).df.label;
        //                         updated_label = get_updated_label(frm, section_with_ext);
        //                         //console.log("Label is ", orig_label)
        //                         //console.log("Updated abel is ", updated_label)
        //                         //console.log(title_extns)
        //                         if (!(updated_label.toLowerCase().includes("changed"))) {
        //                             //console.log("XX")
        //                             frm.set_df_property(section_with_ext, "label", orig_label + " <span style=\"background-color: yellow;\"><i> (Field Changed) </i></span>");
        //                             frm.get_field(section_with_ext).refresh()
        //                         }
        //                             //title_extns.push(extns[ext]+" added")
        //                             //frm.set_df_property(fieldname, "label", label + " <span style=\"background-color: yellow;\"><i>("+extns[ext]+" added) </i></span>");                                
        //                     }
        //                 if (section_ext_changed) {
        //                     orig_label = frm.get_field("toggle_"+section).df.label;
        //                     if (!orig_label.toLowerCase().includes("changed")) {
        //                         frm.set_df_property("toggle_"+section, "label", orig_label + " <span style=\"background-color: yellow;\"><i> (Review Section Changed) </i></span>");
        //                         frm.get_field(section_with_ext).refresh()
        //                     }                
        //                 }
        //                     // if (title_extns.length > 0) {
        //                     //     var title_ext_str = "("+title_extns.join(', ')+")"
        //                     //     console.log(title_ext_str)
        //                     //     frm.set_df_property(section_with_ext, "label", label + " <span style=\"background-color: yellow;\"><i>"+title_ext_str+"</i></span>");                        
        //                     // }
                            
        //                     // //console.log(title_extns)
        //                     //     if (title_extns.length > 0) {
        //                     //         var title_ext_str = "("+title_extns.join(', ')+")"
        //                     //         console.log("Setting title to ", title_ext_str)
        //                     //         //frm.set_df_property(section, "label", label + " <span style=\"background-color: yellow;\"><i>"+title_ext_str+"</i></span>");
        //                     //         let head = $(frm.get_field(section).wrapper).find('.section-head');
        //                     //         let head_contents = head.contents().filter(function() { return this.nodeType === 3; })
        //                     //         console.log("Head contents ", head_contents)
        //                     //         head_contents[0].nodeValue = orig_label + " <span style=\"background-color: yellow;\"><i>"+title_ext_str+"</i></span>";                        
        //                     //         //frm.refresh_field(section);
        //                     //     }
        //                 }
        //             }
        //         }
        //     }
        // }


        // Set the word limits for each field
        if (true) {
            for (const field_name in field_word_length_map) {
                //console.log(field_name);
                //console.log(frm.fields_dict[field_name]);
                if (frm.fields_dict.hasOwnProperty(field_name) && frm.fields_dict[field_name].$input) {
                    let field = frm.fields_dict[field_name];
                    if (field && field.$input && field.df.fieldtype !== "Section Break") {                
                        frm.fields_dict[field_name].$input.on("keyup", function () {
                            let value = $(this).val() || "";
                            let words = value.trim().split(/\s+/);

                            if (words.length > field_word_length_map[field_name]) {
                                frappe.msgprint(`Maximum ${field_word_length_map[field_name]} words allowed.`);
                                // Trim extra words
                                $(this).val(words.slice(0, field_word_length_map[field_name]).join(" "));
                            }
                        });
                    }
                }
            }
        }

        // Loop through every field in the DocType and close all review sections
        Object.keys(frm.fields_dict).forEach(fieldname => {
            // If the fieldname ends with '_addons', hide it
            if (fieldname.endsWith('_addons')) {
                frm.set_df_property(fieldname, 'hidden', 1);
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
