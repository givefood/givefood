

function insertAfter(newNode, referenceNode) {
    referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

function titleCase(str) {
    return str.replace(
        /\w\S*/g,
        function(txt) {
            return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
        }
    );
}

function food_titleCase(str) {
  str = titleCase(str);
  str = str.replace(/Uht/g,"UHT");
  str = str.replace(/Bbq/g,"BBQ");
  str = str.replace(/Spf/g,"SPF");
  return str
}

function csvToLines(str) {
  return str.replace(/, /g, "\n");
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

function address_cleanup(str) {
  str = str.replace("Rd\n", "Road\n");
  str = str.replace("St\n", "Street\n");
  str = str.replace("Ln\n", "Lane\n");
  str = str.replace("Cl\n", "Close\n");
  str = str.replace("Ave\n", "Avenue\n");
  str = str.replace("Ct\n", "Court\n");
  return str
}

const name_field = document.querySelector("#id_name");
const lattlong_field = document.querySelector("#id_latt_long");
const place_id_field = document.querySelector("#id_place_id");
const address_field = document.querySelector("#id_address");
const postcode_field = document.querySelector("#id_postcode");
const change_text_field = document.querySelector("#id_change_text");
const excess_change_text = document.querySelector("#id_excess_change_text");
const fb_name_field = document.querySelector(".form-new-food-bank #id_name");
const dp_name_field = document.querySelector(".form-new-donation-point #id_name, .form-edit-donation-point #id_name");

const geolocation_url = "https://maps.googleapis.com/maps/api/geocode/json?region=uk&key=" + gmap_geocode_key + "&address="
const place_url = "/admin/proxy/gmaps/textsearch/?region=uk&key=" + gmap_places_key + "&query="
const place_detail_url = "/admin/proxy/gmaps/placedetails/?region=uk&key=" + gmap_places_key + "&placeid="
const map_url = "https://maps.googleapis.com/maps/api/staticmap?zoom=15&size=300x300&key=" + gmap_static_key + "&scale=2&center="

// Check FB slug
if (fb_name_field) {
  var fb_name_dupe = document.createElement('div');
  insertAfter(fb_name_dupe, fb_name_field);
  fb_name_field.addEventListener("keyup", function(event) {
    fb_name = fb_name_field.value;
    fb_slug = slugify(fb_name);
    api_url = "/api/2/foodbank/" + fb_slug + "/";
    var fb_slug_req = new XMLHttpRequest();
    fb_slug_req.addEventListener("load", function(){
      if (this.status == 404) {
        fb_name_dupe.className = "notification is-success";
        fb_name_dupe.innerHTML = "No food bank with the name '" + fb_name + "'";
      };
      if (this.status == 200) {
        fb_name_dupe.className = "notification is-warning";
        fb_name_dupe.innerHTML = "'" + fb_name + "' food bank already exists";
      }
    });
    fb_slug_req.responseType = "json";
    fb_slug_req.open("GET", api_url);
    fb_slug_req.send();
  })
};

// Donation point lookup
if (dp_name_field) {
  var dp_lookup_btn = document.createElement('div');
  dp_lookup_btn.innerHTML = "<a href='#' id='dp_lookup_btn' class='extra-form-button button is-info'>Lookup Donation Point</a>";
  insertAfter(dp_lookup_btn, dp_name_field);
  dp_lookup_btn.addEventListener("click", function(event) {
    address = name_field.value + ", UK";
    url = place_url + encodeURIComponent(address);
    var place_req = new XMLHttpRequest();
    place_req.addEventListener("load", function(){
      lat = this.response.results[0].geometry.location.lat
      lng = this.response.results[0].geometry.location.lng
      place_id = this.response.results[0].place_id
      lat_lng = lat + "," + lng
      lattlong_field.value = lat_lng
      place_id_field.value = place_id

      map_img = document.createElement('img');
      map_img.src = map_url + lat_lng
      insertAfter(map_img, place_id_field);

      url = place_detail_url + place_id;
      var placedetail_req = new XMLHttpRequest();
      placedetail_req.addEventListener("load", function(){
        address = address_cleanup(this.response.result.formatted_address.replaceAll(", ", "\n"))
        postcode = address.match(/[A-Za-z]{1,2}\d{1,2}(?:\s?(?:\d?\w{2}))?/)
        address = address.replace(" " + postcode, "")
        address_field.value = address
        postcode_field.value = postcode
        if (this.response.result.formatted_phone_number) {
          document.querySelector("#id_phone_number").value = this.response.result.formatted_phone_number
        }
        if (this.response.result.website) {
          document.querySelector("#id_url").value = this.response.result.website
        }
        document.querySelector("#id_opening_hours").value = this.response.result.opening_hours.weekday_text.join("\n")
        if (this.response.result.wheelchair_accessible_entrance) {
          document.querySelector("#id_wheelchair_accessible").value = this.response.result.wheelchair_accessible_entrance
        }
      });
      placedetail_req.responseType = "json";
      placedetail_req.open("GET", url);
      placedetail_req.send();

    });
    place_req.responseType = "json";
    place_req.open("GET", url);
    place_req.send();
    event.preventDefault();
  })
}

// LATTLONG
if (lattlong_field) {
  var get_latlng_btn = document.createElement('div');
  get_latlng_btn.innerHTML = "<a href='#' id='get_latlng_btn' class='extra-form-button button is-info'>Get Lat/Lng &amp; Place ID</a>";
  insertAfter(get_latlng_btn, lattlong_field);
  latlng_btn = document.querySelector("#get_latlng_btn");
  latlng_btn.addEventListener("click", function(event) {
    address = name_field.value + ", " + address_field.value.replace(/\n/g,", ") + ", " + postcode_field.value;
    url = geolocation_url + encodeURIComponent(address);
    var gl_req = new XMLHttpRequest();
    gl_req.addEventListener("load", function(){
      lat = this.response.results[0].geometry.location.lat
      lng = this.response.results[0].geometry.location.lng
      place_id = this.response.results[0].place_id
      lat_lng = lat + "," + lng
      lattlong_field.value = lat_lng
      place_id_field.value = place_id
      map_img = document.createElement('img');
      map_img.src = map_url + lat_lng
      insertAfter(map_img, place_id_field);
    });
    gl_req.responseType = "json";
    gl_req.open("GET", url);
    gl_req.send();
    event.preventDefault();
  })
};


// CHANGETEXT
if (change_text_field) {
  var titlecase_btn = document.createElement('div');
  var csvline_btn = document.createElement('div');
  var findreplace_btn = document.createElement('div');

  titlecase_btn.innerHTML = "<a href='#' id='titlecase_btn' class='extra-form-button button is-info'>Make Titlecase</a>";
  csvline_btn.innerHTML = "<a href='#' id='csvline_btn' class='extra-form-button button is-info'>CSV to Lines</a>";
  findreplace_btn.innerHTML = "<a href='#' id='findreplace_btn' class='extra-form-button button is-info'>Find & Replace</a>";

  insertAfter(csvline_btn, change_text_field);
  insertAfter(findreplace_btn, change_text_field);
  insertAfter(titlecase_btn, excess_change_text);

  titlecase_btn = document.querySelector("#titlecase_btn");
  titlecase_btn.addEventListener("click", function(event) {
    change_text_field.value = food_titleCase(change_text_field.value)
    excess_change_text.value = food_titleCase(excess_change_text.value)
    event.preventDefault();
  });

  csvline_btn = document.querySelector("#csvline_btn");
  csvline_btn.addEventListener("click", function(event) {
    change_text_field.value = csvToLines(change_text_field.value);
    event.preventDefault();
  });

  findreplace_btn = document.querySelector("#findreplace_btn");
  findreplace_btn.addEventListener("click", function(event) {
    find_text = prompt("Find what?");
    replace_text = prompt("Replace with what?");
    change_text_field.value = change_text_field.value.replaceAll(find_text,replace_text)
    event.preventDefault();
  });
};