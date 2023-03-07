const foodbank_geojson_url = "/api/2/foodbanks/?format=geojson"
const location_geojson_url = "/api/2/locations/?format=geojson"

var map_main

function move_map(lat,lng) {
    map_main.panTo(new google.maps.LatLng(lat,lng));
    map_main.setZoom(12);
}

function add_potential_marker(lat, lng, the_name) {
    var marker = new google.maps.Marker({
        position: {"lat": lat, "lng": lng},
        map: map_main,
        title: the_name,
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

function init_map() {
    map_main = new google.maps.Map(document.getElementById("map"), {
        center: new google.maps.LatLng(55,-4),
        zoom: 6,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });

    map_main.data.loadGeoJson(foodbank_geojson_url);
    map_main.data.loadGeoJson(location_geojson_url);

    map_main.data.addListener('click', (event) => {
        const url = event.feature.getProperty('url');
        window.location = url.replace("https://www.givefood.org.uk","")
    });

    if (typeof initial_lat_lng !== 'undefined') {
        split_lat_lng = initial_lat_lng.split(",")
        lat = parseFloat(split_lat_lng[0])
        lng = parseFloat(split_lat_lng[1])
        move_map(lat,lng)
    }

    document.querySelectorAll("#results li").forEach((li) => {
        lat = parseFloat(li.dataset.lat)
        lng = parseFloat(li.dataset.lng)
        the_name = li.dataset.name
        add_potential_marker(lat, lng, the_name)
    })

}

google.maps.event.addDomListener(window, 'load', init_map);