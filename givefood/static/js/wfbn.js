const address_field = document.querySelector("#address_field");
const lat_lng_field = document.querySelector("#lat_lng_field");
const burger_menu = document.querySelector(".navbar-burger");
const menu_items = document.querySelectorAll(".foodbank-menu li a");
const uml_btn = document.querySelector("#usemylocationbtn");
const addressform = document.querySelector("#addressform");
const convert_ids = ["donate_btn", "bankuet_btn", "updates_btn", "takeaction_btn", "website_link", "email_link", "charity_link", "subscribe_btn"];
const status_msg = document.querySelector("#status-msg");
const results_table = document.querySelector("table");
const index_intro = document.querySelector("#index_intro")
const modal = document.querySelector(".modal");
const modal_close = document.querySelector(".modal-close");

const api_url_root = "/api/2/locations/search/";
const ip_geolocation_url = "/needs/getlocation/"

const working_html = "<img src='/static/img/loading.svg' alt='Loading'> Getting nearby foodbanks...";
const requesting_loc_html = "<img src='/static/img/loading.svg' alt='Loading'> Requesting your location...";
const no_loc_apology_text = "Sorry, we tried to get your location automatically but couldn't. Try a postcode or address.";
const no_addr_text = "Did you forget to enter an address?";
const nothing_needed_text = "Nothing right now, thanks";
const check_facebook_text = "Check the food bank's Facebook page for what they need";
const need_unknown_text = "Sorry. We don't know what's needed here, please contact the food bank";
const loc_not_uk = "Sorry, we couldn't use that location. Is it inside the United Kingdom?";
const search_error = "Sorry, we had a problem finding food banks there. The error was logged. Please try again later."


function init() {
    if (addressform) {
      autocomplete = new google.maps.places.Autocomplete(address_field, {types:["geocode"]});
      autocomplete.setComponentRestrictions({'country': ['gb', 'im', 'je', 'gg']});
      autocomplete.addListener("place_changed", () => {
        lat_lng_field.value = autocomplete.getPlace().geometry.location.lat() + "," + autocomplete.getPlace().geometry.location.lng();
      })
      addressform.addEventListener("submit", do_address);
      if (uml_btn) {
        if (uml_btn.hasAttribute("data-is-homepage")) {
          uml_btn.addEventListener("click", function(event){
            event.preventDefault();
            uml_click(true);
          });
        } else {
          uml_btn.addEventListener("click", function(event){
            event.preventDefault();
            uml_click(false);
          });
        }
      }
    }
    if (burger_menu) {
      burger_menu.addEventListener('click',function(){
          for (const menu_item of menu_items) {
              menu_item.style.display = 'block';
          }
          burger_menu.style.display = 'none';
      })
    };
    if (modal_close) {
      modal_close.addEventListener("click", function(){
        modal.classList.remove("is-active")
      })
    }
    convert_ids.forEach(function(the_id) {
      the_element = document.querySelector("#" + the_id)
      if (the_element) {
        the_element.addEventListener("click", record_conversion)
      }
    });
}

function record_conversion() {
  gtag('event', 'conversion', {'send_to': 'AW-448372895/rBD8CKOqkPABEJ_B5tUB'});
  plausible('conversion')
}

function uml_click(redirect) {
  uml_btn.classList.add("working")
  if (redirect) {
    do_geolocation_redirect()
  } else {
    do_geolocation()
  }
}

function do_geolocation_redirect() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function(position){
          lat  = position.coords.latitude;
          lng = position.coords.longitude;
          address_field.value = "";
          window.location = "/needs/?lat_lng=" + lat + "," + lng;
      }
    );
  }
}

function do_geolocation() {
  clear_results();
  if (!navigator.geolocation) {
    window.location = ip_geolocation_url
  } else {
    status_msg.innerHTML = requesting_loc_html;
    navigator.geolocation.getCurrentPosition(
      do_latlng,
      function() {
        window.location = ip_geolocation_url
      }
    );
  }
}

function do_address(event) {
  clear_results();
  address = address_field.value;
  if (address == "") {
    status_msg.textContent = no_addr_text;
  } else {
    querystring = "?address=" + address;
    api_url = api_url_root + querystring;
    api_request(api_url);
    address_on_map(address)
    record_search(querystring);
    history.pushState({address: address}, "address", querystring)
  }
  event.preventDefault();
}

function do_latlng(position) {
  lat  = position.coords.latitude;
  lng = position.coords.longitude;
  address_field.value = ""
  querystring = "?lat_lng=" + lat + "," + lng;
  api_url = api_url_root + querystring;
  api_request(api_url);
  move_map(lat,lng)
  record_search(querystring);
  history.pushState({latlng: lat + "," + lng}, "latlng", querystring)
}

function address_on_map(address) {
  address = address + ",UK"
  geocoder = new google.maps.Geocoder();
  geocoder.geocode({address:address}, function(results, status) {
    move_map(results[0].geometry.location.lat(),results[0].geometry.location.lng());
  })
}

function move_map(lat,lng) {
  if (typeof map_main !== 'undefined') {
    map_main.panTo(new google.maps.LatLng(lat,lng));
    map_main.setZoom(13);
    var marker = new google.maps.Marker({
      position: {"lat": lat, "lng": lng},
      map: map_main,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 6,
        fillOpacity: 1,
        strokeWeight: 2,
        fillColor: '#5384ED',
        strokeColor: '#ffffff',
      },
    });
  }
}

function record_search(querystring) {
  gtag('config', 'UA-153866507-1', {
    'page_title' : 'What Food Banks Need',
    'page_path': '/needs/' + querystring
  });
}

function api_request(url) {
  if (status_msg) {
    status_msg.innerHTML = working_html;
  }
  var fb_req = new XMLHttpRequest();
  fb_req.addEventListener("load", api_response);
  fb_req.responseType = "json";
  fb_req.open("GET", url);
  fb_req.send();
}

function clear_results() {
  while (results_table.firstChild) {
    results_table.removeChild(results_table.firstChild);
  }
  if (index_intro) {
    index_intro.style.display = "none";
  }
}

function add_click_recorders() {
  document.querySelector("a.foodbank").addEventListener("click", record_click);
}

function record_click() {
  gtag('event', 'conversion', {'send_to': 'AW-448372895/rBD8CKOqkPABEJ_B5tUB'});
  plausible('conversion');
}

function api_response() {

  if (this.status != 200) {
    if (this.status == 400) {
      status_msg.innerHTML = loc_not_uk;
    } else {
      status_msg.innerHTML = search_error;
    }
    return false;
  }

  template = document.querySelector("#fb_row");

  for (loctnidx in this.response) {

    loctn = this.response[loctnidx];

    gf_url = loctn.urls.html
    url = loctn.urls.homepage;
    fb_name = loctn.name;
    distance = loctn.distance_mi;
    slug = loctn.foodbank.slug;
    number_needs = loctn.needs.number;
    org_type = loctn.type;
    parent_org = loctn.foodbank.name;
    parent_org_slug = loctn.foodbank.slug;
    phone = loctn.phone;
    needs = loctn.needs.needs;
    needs_html = needs.replace(/\n/g, "<br>");

    currentrow = document.importNode(template.content, true);
    currentrow.querySelector("a.foodbank").href = url;
    currentrow.querySelector("a.foodbank").textContent = fb_name;
    if (org_type == "location" && currentrow.querySelector(".parent_org")) {
      currentrow.querySelector(".parent_org span").innerHTML = "Part of"
      currentrow.querySelector(".parent_org a").innerHTML = parent_org;
      currentrow.querySelector(".parent_org a").href = "/needs/at/" + parent_org_slug + "/";
    }
    currentrow.querySelector(".distance span").textContent = distance;
    if (number_needs > 0 && needs != "Nothing" && needs != "Unknown" && needs != "Facebook") {
      if (number_needs > 1) {item_text = "items"} else {item_text = "item"};
      currentrow.querySelector(".fb_needs p").innerHTML = needs_html;
      currentrow.querySelector(".subscribe").href = "/needs/at/" + parent_org_slug + "/subscribe/";
    } else if (needs == "Unknown") {
      currentrow.querySelector(".fb_needs").innerHTML = need_unknown_text;
      currentrow.querySelector(".subscribe").remove()
    } else if (needs == "Facebook") {
      currentrow.querySelector(".fb_needs").innerHTML = check_facebook_text;
      currentrow.querySelector(".subscribe").remove()
    } else {
      currentrow.querySelector(".fb_needs").innerHTML = nothing_needed_text;
      currentrow.querySelector(".subscribe").remove()
    }
    if (currentrow.querySelector(".links")) {
      currentrow.querySelector(".links .phone").href = "tel:" + phone;
      currentrow.querySelector(".links .info").href = gf_url.replace("https://www.givefood.org.uk","");
    }
    if (!phone) {
      currentrow.querySelector(".links .phone").remove();
    }
    results_table.appendChild(currentrow);
  }
  add_click_recorders();
  if (status_msg) {
    status_msg.innerHTML = "";
  }
  uml_btn.classList.remove("working")
}

function show_subscribe_modal() {
  fb_name = this.getAttribute("data-foodbankname")
  modal.querySelector("form").setAttribute("action","/needs/at/" + slugify(fb_name) + "/updates/subscribe/")
  modal.querySelector(".foodbank-name").innerHTML = fb_name
  modal.classList.add("is-active")
  record_conversion()
}

function slugify(str) {
  str = str.replace(/^\s+|\s+$/g, ''); // trim
  str = str.toLowerCase();

  // remove accents, swap ñ for n, etc
  var from = "àáäâèéëêìíïîòóöôùúüûñç·/_,:;";
  var to   = "aaaaeeeeiiiioooouuuunc------";
  for (var i=0, l=from.length ; i<l ; i++) {
      str = str.replace(new RegExp(from.charAt(i), 'g'), to.charAt(i));
  }

  str = str.replace(/[^a-z0-9 -]/g, '') // remove invalid chars
      .replace(/\s+/g, '-') // collapse whitespace and replace by -
      .replace(/-+/g, '-'); // collapse dashes

  return str;
}

init();


document.addEventListener("keydown", function(event) {
  const key = event.key;
  if (key === "Escape") {
    modal.classList.remove("is-active")
  }
});