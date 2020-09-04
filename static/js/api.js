const default_method = "foodbanks"
const default_format = "json"
const api_domain = "https://www.givefood.org.uk"

function escaper(html){
    var text = document.createTextNode(html);
    var p = document.createElement('p');
    p.appendChild(text);
    return p.innerHTML;
  }

function init() {

    document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightBlock(block);
    });

    method_links = document.querySelectorAll("#api_methods a")
    method_links.forEach((method_link) => {
        method_link.addEventListener('click', function(event) {
        method_name = this.innerHTML
        show_method(method_name)
      })
    })

    argument_changers = document.querySelectorAll("select.api_format, select.api_method_argument")
    argument_changers.forEach((argument_changer) => {
        argument_changer.addEventListener('change', function(event) {
            get_api_result()
      })
    })

    clipboard_btns = document.querySelectorAll(".clipboard")
    clipboard_btns.forEach((clipboard_btn) => {
        clipboard_btn.addEventListener('click', function(event) {
            url = document.querySelector(".api_method.active .method_url").value
            navigator.clipboard.writeText(url)
      })
    })

    openurl_btns = document.querySelectorAll(".openurl")
    openurl_btns.forEach((openurl_btn) => {
        openurl_btn.addEventListener('click', function(event) {
            url = document.querySelector(".api_method.active .method_url").value
            window.open(url)
      })
    })

    show_method(default_method)

}


function show_method(method_name) {
    console.log("Showing method " + method_name)

    const method_panes = document.querySelectorAll(".api_method")
    method_panes.forEach((method_pane) => {
        method_pane.classList.remove("active")
    })
    method_pane = document.querySelector("#" + method_name)
    method_pane.classList.add("active")

    get_api_result()

}


function get_api_result() {

    method_name = document.querySelector(".api_method.active").getAttribute("id")
    url = document.querySelector("#" + method_name).getAttribute("data-method-url")

    argument_fields = document.querySelector("#" + method_name).querySelectorAll(".api_method_argument")
    argument_fields.forEach((argument_field) => {
        console.log("Found argument '" + argument_field.name + "' with value '" + argument_field.value + "'")
        url = url.replace(":" + argument_field.name + ":",argument_field.value)
    })
    format = document.querySelector("#" + method_name).querySelector(".api_format").value
    console.log("Found format '" + format + "'")
    if (format != default_format) {
        url = url + "?format=" + format
    }

    full_url = api_domain + url
    document.querySelector("#" + method_name + " .method_url").value = full_url

    console.log("Calling API with " + url)
    method_pane_results = document.querySelector(".api_method.active code")
    method_pane_results.innerHTML = "Loading..."
    var api_request = new XMLHttpRequest();
    api_request.addEventListener("load", populate_api_result);
    api_request.open("GET", url);
    api_request.send();

}


function populate_api_result() {
    format = document.querySelector(".api_method.active .api_format").value
    method_pane_results = document.querySelector(".api_method.active code")
    method_pane_results.setAttribute("class","")
    method_pane_results.setAttribute("class","language-" + format)
    method_pane_results.innerHTML = escaper(this.responseText)
    hljs.highlightBlock(method_pane_results);
}

document.addEventListener('DOMContentLoaded', (event) => init())