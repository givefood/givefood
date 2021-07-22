const foodbank_geojson_url = "/api/2/foodbanks/?format=geojson"
const location_geojson_url = "/api/2/locations/?format=geojson"

var map_main

function init_map() {
    map_main = new google.maps.Map(document.getElementById("map-main"), {
        center: new google.maps.LatLng(55,-4),
        zoom: 6,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });

    map_main.data.loadGeoJson(foodbank_geojson_url);
    map_main.data.loadGeoJson(location_geojson_url);

    map_main.data.addListener('click', (event) => {
        const url = event.feature.getProperty('url');
        window.location = url
    });

}

google.maps.event.addDomListener(window, 'load', init_map);