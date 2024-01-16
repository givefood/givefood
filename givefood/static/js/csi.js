document.addEventListener("DOMContentLoaded", (event) => {
    document.querySelectorAll("*[data-csi]").forEach((element) => {
        url = element.getAttribute("data-csi");
        fetch(url).then((response) => {
            response.text().then((text) => {
                element.innerHTML = text;
            });
        });
    });
});