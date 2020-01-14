const status = document.querySelector("#status");
const postcode_form = document.querySelector("#postcodeform");
const postcode_field = document.querySelector("#postcodeform input");
const api_url_root = "/api/foodbanks/";

const working_html = "<img src='/static/img/loading.gif' alt='Loading'> Getting nearby foodbanks...";
const requesting_loc_html = "<img src='/static/img/loading.gif' alt='Loading'> Requesting your location...";
const no_loc_apology_text = "Sorry, we tried to get your location automatically but couldn't. Put your postcode in here instead.";
const nothing_needed_text = "Nothing right now, thanks";
const postcode_error_text = "Sorry, we didn't understand that. Is the postcode valid?";

if (!navigator.geolocation) {
  display_postcode_form();
} else {
  status.innerHTML = requesting_loc_html;
  navigator.geolocation.getCurrentPosition(
    do_lattlong,
    display_postcode_form
  );
}

function display_postcode_form() {
  status.textContent = no_loc_apology_text;
  postcode_form.addEventListener("submit", do_postcode);
  postcode_form.style.display = "block";
}

function do_postcode(event) {
  postcode = postcode_field.value;
  api_url = api_url_root + "?postcode=" + postcode;
  api_request(api_url);
  event.preventDefault();
}

function do_lattlong(position) {
  latt  = position.coords.latitude;
  long = position.coords.longitude;
  api_url = api_url_root + "?lattlong=" + latt + "," + long;
  api_request(api_url);
  postcode_form.style.display = "none";
}

function api_request(url) {
  status.innerHTML = working_html;
  var fb_req = new XMLHttpRequest();
  fb_req.addEventListener("load", api_response);
  fb_req.responseType = "json";
  fb_req.open("GET", url);
  fb_req.send();
}

function api_response() {

  if (this.status == 500) {
    status.textContent = postcode_error_text;
    return false;
  }

  template = document.querySelector("#fb_row");
  table = document.querySelector("table");

  for (i in this.response) {

    foodbank = this.response[i];

    url = foodbank.shopping_list_url;
    name = foodbank.name;
    distance = foodbank.distance_mi;
    number_needs = foodbank.number_needs;
    needs = foodbank.needs;
    needs_html = needs.replace(/\n/g, "<br>");
    updated_text = foodbank.updated_text;

    currentrow = document.importNode(template.content, true);
    currentrow.querySelector("a").href = url;
    currentrow.querySelector("a").textContent = name;
    currentrow.querySelector(".distance span").textContent = distance;
    if (number_needs > 0 && needs != "Nothing") {
      if (number_needs > 1) {item_text = "items"} else {item_text = "item"};
      currentrow.querySelector("summary").textContent = number_needs + " " + item_text;
      currentrow.querySelector("details p").innerHTML = needs_html;
    } else {
      currentrow.querySelector(".fb_needs").innerHTML = nothing_needed_text;
    }
    currentrow.querySelector(".updated span").textContent = updated_text;
    table.appendChild(currentrow);
  }

  status.innerHTML = "";
}
