document.addEventListener("DOMContentLoaded", (event) => {
    document.querySelectorAll("*[data-include]").forEach((element) => {
        const url = element.getAttribute("data-include");
        const updateInterval = element.getAttribute("data-update");
        
        const loadContent = () => {
            fetch(url).then((response) => {
                response.text().then((text) => {
                    element.innerHTML = text;
                });
            });
        };
        
        // Load content initially
        loadContent();
        
        // Set up auto-update if data-update attribute is present
        if (updateInterval) {
            const intervalMs = parseInt(updateInterval) * 1000;
            setInterval(loadContent, intervalMs);
        }
    });
});