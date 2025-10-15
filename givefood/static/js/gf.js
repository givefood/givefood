document.addEventListener('DOMContentLoaded', () => {
    // Remove text fragment identifier from URL after page load
    // Text fragments (#:~:text=) are used by browsers for scroll-to-text
    // but we want to clean them from the URL after the browser has processed them
    if (window.location.hash.includes(':~:')) {
        // Extract any standard hash (before :~:) to preserve it
        const hashParts = window.location.hash.split(':~:');
        let standardHash = hashParts[0];
        
        // If standardHash is just '#', remove it (no standard hash to preserve)
        if (standardHash === '#') {
            standardHash = '';
        }
        
        // Build clean URL
        const cleanUrl = window.location.pathname + window.location.search + standardHash;
        
        // Replace the URL without reloading the page
        window.history.replaceState(null, '', cleanUrl);
    }
});
