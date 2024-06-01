function init_map() {
    var infowindow = new google.maps.InfoWindow();
    map = new google.maps.Map(document.getElementById("map"), {
        center: new google.maps.LatLng(55.4,-4),
        zoom: 6,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
    });

    var data = new google.maps.Data();
    data.loadGeoJson(gf_map_config.geojson, null, function(){
        if (typeof gf_map_config.lat == 'undefined') {
            bounds = new google.maps.LatLngBounds();
            data.forEach(function(feature) {
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
    data.setStyle(function(feature) {
        if (feature.getProperty("type") == "f") {
            marker_colour = "red"
            marker_size = 34
        } else if (feature.getProperty("type") == "l") {
            marker_colour = "yellow"
            marker_size = 28
        } else if (feature.getProperty("type") == "d") {
            marker_colour = "blue"
            marker_size = 24
        } else if (feature.getProperty("type") == "b") {
            marker_colour = ""
            marker_size = 0
        }
        return {
            icon: {
                url: "/static/img/mapmarkers/" + marker_colour + ".png",
                scaledSize: new google.maps.Size(marker_size, marker_size),
            },
            strokeWeight: 1,
            title: feature.getProperty("name")
        };
    });
    data.addListener('click', (event) => {
        feat = event.feature
        if (feat.getProperty('type') != "b") {
            type = feat.getProperty('type');
            title = feat.getProperty('name');
            url = feat.getProperty('url');
            address = feat.getProperty('address');
            html = "<div class='infowindow'><h3>" + title + "</h3>"
            if (type != "f") {
                if (type == "l") {
                    html += "<p>Location for "
                } else {
                    html += "<p>Donation point for "
                }
                html += "<a href='/needs/at/" + slugify(feat.getProperty('foodbank')) + "/'>" + feat.getProperty('foodbank') + "</a> Food Bank.</p>"
            }
            html += "<address>" + address.replace(/(\r\n|\r|\n)/g, '<br>') + "</address><a href='" + url + "' class='button is-info is-small'>More Information</a></div>"
            infowindow.setContent(html);
            infowindow.setPosition(event.latLng);
            infowindow.setOptions({pixelOffset: new google.maps.Size(0,-28)});
            infowindow.open(map);
        }
    });
    data.setMap(map);
    map.setOptions({styles:[
        {
          "featureType": "administrative.land_parcel",
          "elementType": "labels",
          "stylers": [
            {
              "visibility": "off"
            }
          ]
        },
        {
          "featureType": "poi",
          "elementType": "labels.text",
          "stylers": [
            {
              "visibility": "off"
            }
          ]
        },
        {
          "featureType": "road.local",
          "elementType": "labels",
          "stylers": [
            {
              "visibility": "off"
            }
          ]
        }
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