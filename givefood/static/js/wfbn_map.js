function init_map() {
    map_main = new google.maps.Map(document.getElementById("map"), {
        center: new google.maps.LatLng(55.4,-4),
        zoom: 6,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });

    var data_layer = new google.maps.Data();
    data_layer.loadGeoJson(gf_map_config.geojson, null, function(){
        if (typeof gf_map_config.lat == 'undefined') {
            bounds = new google.maps.LatLngBounds();
            data_layer.forEach(function(feature) {
                geo = feature.getGeometry();
                geo.forEachLatLng(function(LatLng) {
                    bounds.extend(LatLng);
                });
            });
            if (gf_map_config.allow_zoom) {
                google.maps.event.addListenerOnce(map, 'bounds_changed', function(event) {
                    var maxZoom = 15
                    if (map.getZoom() > maxZoom) {
                        map.setZoom(maxZoom);
                    }
                });
            }
            map_main.fitBounds(bounds,{left:50, right:50, bottom:50, top:50});
            map_main.panToBounds(bounds);
        }
        legendtemplate = document.querySelector("#legendtemplate").content.cloneNode(true)
        legend = legendtemplate.querySelector("#legend")
        map_main.controls[google.maps.ControlPosition.LEFT_BOTTOM].push(legend);
        legend.style.display = "block";
    });
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

    if (typeof gf_map_config.lat !== 'undefined') {
        move_map(
            gf_map_config.lat,
            gf_map_config.lng,
            gf_map_config.zoom,
        )
    }
}

var map_main
google.maps.event.addDomListener(window, 'load', init_map);