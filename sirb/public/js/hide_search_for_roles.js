// Global Desk script
// your_app/public/js/logout_cleaner.js
// $(document).on('logout', function() {
//     // Clear all frappe-specific local storage
//     console.log("!!")
//     Object.keys(localStorage).forEach(key => {
//         if (key.includes('frappe')) {
//             console.log("clearing ", key)
//             localStorage.removeItem(key);
//         }
//     });
    
//     // Clear session storage as well
//     sessionStorage.clear();
// });
// your_app/public/js/force_cleanup.js
// your_app/public/js/force_cleanup.js

(function() {
    // console.log("!!!")
    // try {
    //     localStorage.removeItem("current_page");
    //     localStorage.removeItem("route_history");
    // } catch (e) {}    
    if (!frappe.boot || !frappe.boot.user) return;

    const roles = frappe.boot.user.roles || [];
    // const targetRole = "Anchor";

    // Only hide for target role, not admins/system managers
    if (roles.includes("Administrator") || roles.includes("System Manager")) return;

    // Function to hide the search bar
    function hideSearchBar() {
        // Option 1: CSS injection (Most reliable for immediate hide)
        const style = document.createElement('style');
        style.innerHTML = `
            .search-bar, 
            .navbar-search, 
            #navbar-search {
                display: none !important;
            }
            /* Hide the Help Dropdown (?) */
            .nav-item.dropdown-help { display: none !important; }
        `;
        document.head.appendChild(style);

        // Option 2: DOM Removal (As a backup once the navbar loads)
        frappe.ui.toolbar.setup_search = function() {
            return; // Overrides the search setup function to do nothing
        };
    }

    // Try hiding immediately in case it's already in the DOM
    hideSearchBar();

    // Set up MutationObserver to catch dynamic navbar injection
    const observer = new MutationObserver(() => hideSearchBar());
    observer.observe(document.body, { childList: true, subtree: true });
})();
