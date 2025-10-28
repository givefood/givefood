document.addEventListener("DOMContentLoaded", (event) => {
    document.querySelectorAll("*[data-include]").forEach((element) => {
        const url = element.getAttribute("data-include");
        const updateInterval = element.getAttribute("data-update");
        
        const loadContent = () => {
            fetch(url, {cache: 'default', priority: 'auto', credentials: 'same-origin'}).then((response) => {
                response.text().then((text) => {
                    element.innerHTML = text;
                });
            });
        };
        
        // Load content initially
        loadContent();
        
        // Set up auto-update if data-update attribute is present
        if (updateInterval) {
            const intervalSeconds = parseInt(updateInterval, 10);
            if (intervalSeconds > 0) {
                setInterval(loadContent, intervalSeconds * 1000);
            }
        }
    });
});