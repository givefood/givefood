document.addEventListener("DOMContentLoaded", (event) => {
    document.querySelectorAll("*[data-include]").forEach((element) => {
        url = element.getAttribute("data-include");
        fetch(url).then((response) => {
            response.text().then((text) => {
                element.innerHTML = text;
            });
        });
    });
});