const ip_geolocation_url = "/needs/getlocation/"
const address_field = document.querySelector("#address_field");
const lat_lng_field = document.querySelector("#lat_lng_field");
const burger_menu = document.querySelector(".navbar-burger");
const menu_items = document.querySelectorAll(".foodbank-menu li a");
const uml_btn = document.querySelector("#usemylocationbtn");
const addressform = document.querySelector("#addressform");
const map_element = document.querySelector("#map");

function init() {
    if (map_element) {
      init_map()
    }
    if (addressform) {
      autocomplete = new google.maps.places.Autocomplete(address_field, {types:["geocode"]});
      autocomplete.setComponentRestrictions({'country': ['gb', 'im', 'je', 'gg']});
      autocomplete.addListener("place_changed", () => {
        lat_lng_field.value = autocomplete.getPlace().geometry.location.lat() + "," + autocomplete.getPlace().geometry.location.lng();
      })
      if (uml_btn) {
        uml_btn.addEventListener("click", function(event){
            event.preventDefault();
            uml_btn.classList.add("working");
            url = uml_btn.getAttribute("data-url")
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                  function(position){
                      lat  = position.coords.latitude;
                      lng = position.coords.longitude;
                      address_field.value = "";
                      window.location = url + "?lat_lng=" + lat + "," + lng;
                  }
                );
            }
        });
      }
    }
    if (burger_menu) {
      burger_menu.addEventListener('click',function(){
          for (const menu_item of menu_items) {
              menu_item.style.display = 'block';
          }
          burger_menu.style.display = 'none';
      })
    };
}

function move_map(lat,lng,zoom) {
    if (typeof map !== 'undefined') {
      map.panTo(new google.maps.LatLng(lat,lng));
      map.setZoom(zoom);
      if (gf_map_config.location_marker == true) {
        var marker = new google.maps.Marker({
          position: {"lat": lat, "lng": lng},
          map: map,
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
    }
}

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
        if (document.querySelector("#legendtemplate")) {
            legendtemplate = document.querySelector("#legendtemplate").content.cloneNode(true)
            legend = legendtemplate.querySelector("#legend")
            map.controls[google.maps.ControlPosition.LEFT_BOTTOM].push(legend);
            legend.style.display = "block";
        }
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
            html = "<div class='infowindow'>"
            html += "<h3>" + title + "</h3>"
            if (type != "f") {
                if (type == "l") {
                    html += "<p>Location for "
                } else {
                    html += "<p>Donation point for "
                }
                html += "<a href='/needs/at/" + slugify(feat.getProperty('foodbank')) + "/'>" + feat.getProperty('foodbank') + "</a> Food Bank.</p>"
            }
            if (address) {
                html += "<address>" + address.replace(/(\r\n|\r|\n)/g, '<br>') + "</address>"
            }
            html += "<a href='" + url + "' class='button is-info is-small'>More Information</a></div>"
            infowindow.setContent(html);
            infowindow.setPosition(event.latLng);
            infowindow.setOptions({
                maxWidth: 250,
                pixelOffset: new google.maps.Size(0,-28),
            });
            infowindow.open(map);
        }
    });
    data.setMap(map);
    map.setOptions({styles:[
        {
          "featureType": "poi",
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