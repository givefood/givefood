const geojson_url = "/needs/geo.json"

var map_main

function init_map() {
    map_main = new google.maps.Map(document.getElementById("map"), {
        center: new google.maps.LatLng(55.4,-4),
        zoom: 6,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });

    var data_layer = new google.maps.Data();
    data_layer.loadGeoJson(geojson_url);
    data_layer.setStyle(function(feature) {
        if (feature.getProperty("type") == "fb") {
            marker_colour = "red"
            marker_size = 32
        } else if (feature.getProperty("type") == "loc") {
            marker_colour = "yellow"
            marker_size = 26
        } else if (feature.getProperty("type") == "dp") {
            marker_colour = "blue"
            marker_size = 22
        }
        return {
            icon: {
                url: "/static/img/mapmarkers/" + marker_colour + ".png",
                scaledSize: new google.maps.Size(marker_size, marker_size),
            },
            title: feature.getProperty("name")
        };
    });
    data_layer.addListener('click', (event) => {
        window.location = event.feature.getProperty('url');
    });
    data_layer.setMap(map_main);

    if (typeof initial_lat_lng !== 'undefined') {
        split_lat_lng = initial_lat_lng.split(",")
        lat = parseFloat(split_lat_lng[0])
        lng = parseFloat(split_lat_lng[1])
        move_map(lat,lng)
    }

}

google.maps.event.addDomListener(window, 'load', init_map);