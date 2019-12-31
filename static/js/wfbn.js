const status = document.querySelector("#status");
const postcode_form = document.querySelector("#postcodeform");
const postcode_field = document.querySelector("#postcodeform input");
const api_url_root = "/api/foodbanks/";

const working_text = "Getting nearby foodbanks...";
const requesting_loc_text = "Requesting your location...";
const no_loc_apology_text = 'Sorry, we tried to get your location automatically but couldn\'t. Put your postcode in here instead.';
const nothing_needed_text = 'Nothing needed right now, thanks';

if (!navigator.geolocation) {
  display_postcode_form();
} else {
  status.textContent = requesting_loc_text;
  navigator.geolocation.getCurrentPosition(
    do_lattlong,
    display_postcode_form
  );
}

function display_postcode_form() {
  status.textContent = no_loc_apology_text;
  postcode_form.addEventListener("submit", do_postcode);
  postcode_form.style.display = "";
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
  api_url = api_url_root + "?lattlong=" + latt + ',' + long;
  api_request(api_url);
  postcode_form.style.display = "none";
}

function api_request(url) {
  status.textContent = working_text;
  var fb_req = new XMLHttpRequest();
  fb_req.addEventListener("load", api_response);
  fb_req.responseType = "json";
  fb_req.open("GET", url);
  fb_req.send();
}

function api_response() {

  template = document.querySelector('#fb_row');
  table = document.querySelector('table');

  for (i in this.response) {

    url = this.response[i].shopping_list_url;
    name = this.response[i].name;
    distance = this.response[i].distance_mi;
    number_needs = this.response[i].number_needs;
    needs = this.response[i].needs;
    needs_html = needs.replace(/\n/g, '<br>');
    updated_text = this.response[i].updated_text;

    currentrow = document.importNode(template.content, true);
    currentrow.querySelector("a").href = url;
    currentrow.querySelector("a").textContent = name;
    currentrow.querySelector(".distance span").textContent = distance;
    if (number_needs > 0 && needs != "Nothing") {
      currentrow.querySelector("summary").textContent = number_needs + " items";
      currentrow.querySelector("details p").innerHTML = needs_html;
    } else {
      currentrow.querySelector(".fb_needs").innerHTML = nothing_needed_text;
    }
    currentrow.querySelector(".updated span").textContent = updated_text;
    table.appendChild(currentrow);
  }

  status.innerHTML = "";
}
