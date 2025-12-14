
$(document).ready(function(){
    // Roles that should NOT see the global search bar
    console.log("Hi!");

    // const blocked_roles = ["Student", "Faculty Mentor", "Primary Reviewer", "Secondary Reviewer", "Anchor"];

    // const current_user = frappe.boot?.user?.name;
    // console.log(current_user);
    // alert(current_user);
    // if (current_user == "Administrator") {
    //     const selectors = [
    //         ".navbar .search-bar",
    //         ".navbar .global-search",
    //         ".navbar .search-box",
    //         ".navbar .dropdown-search"
    //     ];

    //     selectors.forEach(sel => {
    //         const el = document.querySelector(sel);
    //         if (el) el.style.display = "block";
    //     });        
    //     return;
    // }

    // const user_roles = frappe.boot.user.roles || [];

    // if (user_roles.some(r => blocked_roles.includes(r))) {

    //     // All known selectors for the search bar in v14–v15
    //     const selectors = [
    //         ".navbar .search-bar",
    //         ".navbar .global-search",
    //         ".navbar .search-box",
    //         ".navbar .dropdown-search"
    //     ];

    //     selectors.forEach(sel => {
    //         const el = document.querySelector(sel);
    //         if (el) el.style.display = "none";
    //     });
    // }
});
