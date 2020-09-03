const default_method = "foodbanks"

function init() {

    document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightBlock(block);
    });

    const method_links = document.querySelectorAll("#api_methods a")
    for (const method_link of method_links) {
    method_link.addEventListener('click', function(event) {
        method_name = this.innerHTML
        show_method(method_name)
      })
    }

    show_method(default_method)

}


function show_method(method_name) {
    console.log("Showing method " + method_name)

    const method_panes = document.querySelectorAll(".api_method")
    for (const method_pane of method_panes) {
        method_pane.classList.remove("active")
    }
    method_pane = document.querySelector("#" + method_name)
    method_pane.classList.add("active")

    get_api_result()

}


function get_api_result() {

    method_name = document.querySelector(".api_method.active").getAttribute("id")
    url = document.querySelector("#" + method_name + " .method_url").value

    console.log("Calling API with " + url)
    var api_request = new XMLHttpRequest();
    api_request.addEventListener("load", populate_api_result);
    api_request.open("GET", url);
    api_request.send();

}


function populate_api_result() {
    method_pane_results = document.querySelector(".api_method.active code")
    method_pane_results.innerHTML = this.responseText
    hljs.highlightBlock(method_pane_results);
}

document.addEventListener('DOMContentLoaded', (event) => init())