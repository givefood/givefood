const address_field = document.querySelector("#address_field");
const burger_menu = document.querySelector(".navbar-burger");
const menu_items = document.querySelectorAll(".foodbank-menu li a");
const uml_btn = document.querySelector("#usemylocationbtn");

function init() {
    autocomplete = new google.maps.places.Autocomplete(address_field, {types:["geocode"]});
    autocomplete.setComponentRestrictions({'country': ['gb']});
    uml_btn.addEventListener("click", do_geolocation);
    burger_menu.addEventListener('click',function(){
        for (const menu_item of menu_items) {
            menu_item.style.display = 'block';
        }
        burger_menu.style.display = 'none';
    })
}

function do_geolocation(event) {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        function(position){
            lat  = position.coords.latitude;
            lng = position.coords.longitude;
            address_field.value = ""
            window.location = "/needs/?lat_lng=" + lat + "," + lng;
        }
      );
    }
    event.preventDefault();
  }

init();