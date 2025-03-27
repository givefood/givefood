document.querySelector(".dropdown-trigger button").addEventListener("mouseenter", function() {
    document.querySelectorAll(".dropdown-content a").forEach(function(el) {
        document.querySelector("head").insertAdjacentHTML('beforeend','<link rel="prefetch" href="' + el.href + '">');
    });
});