function insertAfter(newNode, referenceNode) {
    referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

const lattlong_field = document.querySelector("#id_latt_long");
const address_field = document.querySelector("#id_address")
const postcode_field = document.querySelector("#id_postcode")

const geolocation_url = "https://maps.googleapis.com/maps/api/geocode/json?key=AIzaSyCgc052pX0gMcxOF1PKexrTGTu8qQIIuRk&address="
const map_url = "https://maps.googleapis.com/maps/api/staticmap?zoom=15&size=300x300&key=AIzaSyCgc052pX0gMcxOF1PKexrTGTu8qQIIuRk&scale=2&center="


if (lattlong_field) {
  var get_lattlong_btn = document.createElement('div');
  get_lattlong_btn.innerHTML = "<a href='#' id='get_lattlong_btn' class='extra-form-button button is-info'>Get LattLong</a>";
  insertAfter(get_lattlong_btn, lattlong_field);
  lattlong_btn = document.querySelector("#get_lattlong_btn");
  lattlong_btn.addEventListener("click", function(event) {
    address = address_field.value.replace(/\n/g,", ") + ", " + postcode_field.value;
    url = geolocation_url + address;
    var gl_req = new XMLHttpRequest();
    gl_req.addEventListener("load", function(){
      latt = this.response.results[0].geometry.location.lat
      long = this.response.results[0].geometry.location.lng
      latt_long = latt + "," + long
      lattlong_field.value = latt_long
      map_img = document.createElement('img');
      map_img.src = map_url + latt_long
      insertAfter(map_img, get_lattlong_btn);
    });
    gl_req.responseType = "json";
    gl_req.open("GET", url);
    gl_req.send();
    event.preventDefault();
  })
}
