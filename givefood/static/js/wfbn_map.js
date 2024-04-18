function init_map() {
    map = new google.maps.Map(document.getElementById("map"), {
        center: new google.maps.LatLng(55.4,-4),
        zoom: 6,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });

    var map_data = new google.maps.Data();
    map_data.loadGeoJson(gf_map_config.geojson, null, function(){
        if (typeof gf_map_config.lat == 'undefined') {
            bounds = new google.maps.LatLngBounds();
            map_data.forEach(function(feature) {
                geo = feature.getGeometry();
                geo.forEachLatLng(function(LatLng) {
                    bounds.extend(LatLng);
                });
            });
            google.maps.event.addListenerOnce(map, 'bounds_changed', function(event) {
                if (gf_map_config.max_zoom) {
                    max_zoom = gf_map_config.max_zoom
                } else {
                    max_zoom = 15
                }
                if (map.getZoom() > max_zoom) {
                    map.setZoom(max_zoom);
                }
            });
            map.fitBounds(bounds,{left:50, right:50, bottom:50, top:50});
            map.panToBounds(bounds);
        }
        legendtemplate = document.querySelector("#legendtemplate").content.cloneNode(true)
        legend = legendtemplate.querySelector("#legend")
        map.controls[google.maps.ControlPosition.LEFT_BOTTOM].push(legend);
        legend.style.display = "block";
    });
    map_data.setStyle(function(feature) {
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
    map_data.addListener('click', (event) => {
        window.location = event.feature.getProperty('url');
    });
    map_data.setMap(map);
    map.setOptions({styles:[
        {
          featureType: "poi.business",
          stylers: [{ visibility: "off" }],
        },
        {
          featureType: "transit",
          elementType: "labels.icon",
          stylers: [{ visibility: "off" }],
        },
      ]
    });

    if (typeof gf_map_config.lat !== 'undefined') {
        move_map(
            gf_map_config.lat,
            gf_map_config.lng,
            gf_map_config.zoom,
        )
    }
}

var map
google.maps.event.addDomListener(window, 'load', init_map);