const foodbank_geojson_url = "/api/2/foodbanks/?format=geojson"
const location_geojson_url = "/api/2/locations/?format=geojson"
const donationpoint_geojson_url = "/api/2/donationpoints/?format=geojson"

var map_main

function init_map() {
    map_main = new google.maps.Map(document.getElementById("map"), {
        center: new google.maps.LatLng(55.4,-4),
        zoom: 6,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });

    // Food Banks
    var fb_layer = new google.maps.Data();
    fb_layer.loadGeoJson(foodbank_geojson_url);
    fb_layer.setStyle(function(feature) {
        return {
            icon: {
                url: "/static/img/mapmarkers/red.png",
                scaledSize: new google.maps.Size(32, 32),
            },
            title: feature.getProperty("name")
        };
    });
    fb_layer.addListener('click', (event) => {
        const url = event.feature.getProperty('url');
        window.location = url.replace("https://www.givefood.org.uk","")
    });
    fb_layer.setMap(map_main);

    // Locations
    var loc_layer = new google.maps.Data();
    loc_layer.loadGeoJson(location_geojson_url);
    loc_layer.setStyle(function(feature) {
        return {
            icon: {
                url: "/static/img/mapmarkers/yellow.png",
                scaledSize: new google.maps.Size(26, 26),
            },
            title: feature.getProperty("name")
        };
    });
    loc_layer.addListener('click', (event) => {
        const url = event.feature.getProperty('url');
        window.location = url.replace("https://www.givefood.org.uk","")
    });
    loc_layer.setMap(map_main);

    // Donation Points
    var dp_layer = new google.maps.Data();
    dp_layer.loadGeoJson(donationpoint_geojson_url);
    dp_layer.setStyle(function(feature) {
        return {
            icon: {
                url: "/static/img/mapmarkers/blue.png",
                scaledSize: new google.maps.Size(22, 22),
            },
            title: feature.getProperty("name")
        };
    });
    dp_layer.addListener('click', (event) => {
        const url = event.feature.getProperty('url');
        window.location = url.replace("https://www.givefood.org.uk","")
    });
    dp_layer.setMap(map_main);

    if (typeof initial_lat_lng !== 'undefined') {
        split_lat_lng = initial_lat_lng.split(",")
        lat = parseFloat(split_lat_lng[0])
        lng = parseFloat(split_lat_lng[1])
        move_map(lat,lng)
    }

}

google.maps.event.addDomListener(window, 'load', init_map);