const address_field = document.querySelector("#address_field");
const burger_menu = document.querySelector(".navbar-burger");
const menu_items = document.querySelectorAll(".foodbank-menu li a");
const uml_btn = document.querySelector("#usemylocationbtn");
const convert_ids = ["donate_btn", "takeaction_btn", "website_link", "phone_link", "email_link", "charity_link", "write_btn"]

function init() {
    autocomplete = new google.maps.places.Autocomplete(address_field, {types:["geocode"]});
    autocomplete.setComponentRestrictions({'country': ['gb']});
    uml_btn.addEventListener("click", do_geolocation);
    if (burger_menu) {
      burger_menu.addEventListener('click',function(){
          for (const menu_item of menu_items) {
              menu_item.style.display = 'block';
          }
          burger_menu.style.display = 'none';
      })
    };
    convert_ids.forEach(function(the_id) {
      the_element = document.querySelector("#" + the_id)
      if (the_element) {
        the_element.addEventListener("click", record_conversion)
      }
    })
}

function record_conversion() {
  gtag('event', 'conversion', {'send_to': 'AW-448372895/rBD8CKOqkPABEJ_B5tUB'});
  plausible('conversion')
}

function do_geolocation(event) {
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
    event.preventDefault();
  }

init();