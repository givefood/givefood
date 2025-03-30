document.querySelector(".dropdown-trigger button").addEventListener("mouseenter", function() {
    document.querySelectorAll(".dropdown-content a").forEach(function(el) {
        if (document.querySelector("link[rel='prefetch'][href='" + el.href + "']") == null) {
            document.querySelector("head").insertAdjacentHTML('beforeend','<link rel="prefetch" href="' + el.href + '">');
        }
    });
});