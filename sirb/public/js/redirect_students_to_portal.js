// Students use the IRB portal (/sirb), not the Desk. Login already sends
// them there (hooks.py add_to_apps_screen), but old bookmarks and links into
// /app would still open the Desk form, so send them on to the same page in
// the portal. Anyone with another IRB role (faculty, reviewers, Anchors,
// programme managers, admins) keeps the Desk.
(function () {
    if (!frappe.boot || !frappe.boot.user) return;
    const roles = frappe.boot.user.roles || [];
    const DESK_ROLES = [
        "Administrator", "System Manager", "Anchor", "IRB Demo",
        "IRB Programme Manager", "IRB Programme Viewer",
        "Faculty Mentor", "Faculty Member", "IRB Reviewer",
        "Primary IRB Reviewer", "Secondary IRB Reviewer",
    ];
    if (!roles.includes("Student") || roles.some((role) => DESK_ROLES.includes(role))) return;

    const project = window.location.pathname.match(/^\/app\/irb-project\/([^/?#]+)/);
    window.location.replace(project ? "/sirb/projects/" + project[1] : "/sirb");
})();
