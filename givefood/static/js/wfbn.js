// Configuration
const IP_GEOLOCATION_URL = "/needs/getlocation/";
const GMAP_MAPID = "d149d3a77fb8625a";

// DOM Elements
const addressField = document.querySelector("#address_field");
const latLngField = document.querySelector("#lat_lng_field");
const useMyLocationBtn = document.querySelector("#usemylocationbtn");
const addressForm = document.querySelector("#addressform");
const mapElement = document.querySelector("#map");

// Global Variables
let map;
let autocomplete;
let googleMapsLoaded = false;
let googleMapsLoading = false;
let autocompleteInitialized = false;

/**
 * Initialize the page functionality
 */
function init() {
    // Check if Google Maps is already loaded (via old callback method)
    if (typeof google !== 'undefined' && google.maps) {
        googleMapsLoaded = true;
        onGoogleMapsLoaded();
        return;
    }

    if (addressForm) {
        // For address autocomplete, we need Google Maps API loaded immediately
        // Load first to avoid race condition with map observer
        loadGoogleMapsAPI();
    } else if (mapElement) {
        // Only use lazy loading if there's no address form
        observeMapElement();
    }

    if (useMyLocationBtn) {
        initLocationButton();
    }
}

/**
 * Observe map element and load Google Maps when it enters viewport
 */
function observeMapElement() {
    // Check if IntersectionObserver is supported
    if (!('IntersectionObserver' in window)) {
        // Fallback: load immediately if IntersectionObserver not supported
        loadGoogleMapsAPI();
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting && !googleMapsLoaded && !googleMapsLoading) {
                loadGoogleMapsAPI();
                // Unobserve after loading starts
                observer.unobserve(mapElement);
            }
        });
    }, {
        // Start loading slightly before element enters viewport
        rootMargin: '50px'
    });

    observer.observe(mapElement);
}

/**
 * Dynamically load Google Maps API
 */
function loadGoogleMapsAPI() {
    if (googleMapsLoaded || googleMapsLoading) {
        return;
    }

    // Check if already loaded by script tag
    if (typeof google !== 'undefined' && google.maps) {
        googleMapsLoaded = true;
        onGoogleMapsLoaded();
        return;
    }

    googleMapsLoading = true;

    // Get configuration from window object set by template
    if (typeof window.gfMapConfig === 'undefined') {
        console.error('Google Maps configuration not found');
        googleMapsLoading = false;
        return;
    }

    const config = window.gfMapConfig;
    const script = document.createElement('script');
    
    // Properly encode URL parameters to prevent injection and handle special characters
    const params = new URLSearchParams({
        key: config.apiKey,
        libraries: config.libraries,
        region: config.region,
        language: config.language
    });
    
    script.src = `https://maps.googleapis.com/maps/api/js?${params.toString()}`;
    script.async = true;
    script.defer = true;

    script.onload = () => {
        // Wait for Google Maps API to be fully initialized
        const checkGoogleMaps = () => {
            if (typeof google !== 'undefined' && google.maps && google.maps.Map) {
                googleMapsLoaded = true;
                googleMapsLoading = false;
                onGoogleMapsLoaded();
            } else {
                // Retry after a short delay if not yet initialized
                setTimeout(checkGoogleMaps, 50);
            }
        };
        checkGoogleMaps();
    };

    script.onerror = () => {
        console.error('Failed to load Google Maps API');
        googleMapsLoading = false;
    };

    document.head.appendChild(script);
}

/**
 * Called when Google Maps API has finished loading
 */
function onGoogleMapsLoaded() {
    if (mapElement) {
        initMap();
    }

    if (addressForm && !autocompleteInitialized) {
        initAddressAutocomplete();
    }
}

/**
 * Initialize Google Places autocomplete
 */
function initAddressAutocomplete() {
    if (autocompleteInitialized) {
        return;
    }
    
    try {
        autocomplete = new google.maps.places.Autocomplete(addressField, {
            types: ["geocode"]
        });
        
        autocomplete.setComponentRestrictions({
            country: ["gb", "im", "je", "gg"]
        });
        
        autocomplete.addListener("place_changed", () => {
            const place = autocomplete.getPlace();
            const location = place.geometry.location;
            latLngField.value = `${location.lat()},${location.lng()}`;
        });
        
        autocompleteInitialized = true;
    } catch (error) {
        console.error('Failed to initialize address autocomplete:', error);
    }
}

/**
 * Initialize "Use My Location" button
 */
function initLocationButton() {
    useMyLocationBtn.addEventListener("click", (event) => {
        event.preventDefault();
        useMyLocationBtn.classList.add("working");
        
        const url = useMyLocationBtn.getAttribute("data-url");
        
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition((position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                addressField.value = "";
                window.location = `${url}?lat_lng=${lat},${lng}`;
            });
        }
    });
}

/**
 * Move map to specified location and add optional marker
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @param {number} zoom - Zoom level
 */
function move_map(lat, lng, zoom) {
    if (typeof map === "undefined") {
        return;
    }

    map.panTo(new google.maps.LatLng(lat, lng));
    map.setZoom(zoom);

    if (window.gfMapConfig.location_marker === true) {
        new google.maps.Marker({
            position: new google.maps.LatLng(lat, lng),
            map: map,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 7,
                fillColor: "#4385F4",
                fillOpacity: 0.8,
                strokeColor: "#fff",
                strokeWeight: 2,
            },
        });
    }
}

/**
 * Convert string to URL-friendly slug
 * @param {string} str - String to slugify
 * @returns {string} Slugified string
 */
function slugify(str) {
    str = str.replace(/^\s+|\s+$/g, "").toLowerCase();

    const from = "àáäâèéëêìíïîòóöôùúüûñç·/_,:;";
    const to = "aaaaeeeeiiiioooouuuunc------";
    
    for (let i = 0; i < from.length; i++) {
        str = str.replace(new RegExp(from.charAt(i), "g"), to.charAt(i));
    }

    str = str
        .replace(/[^a-z0-9 -]/g, "")
        .replace(/\s+/g, "-")
        .replace(/-+/g, "-");

    return str;
}

/**
 * Initialize Google Map with food bank locations
 */
function initMap() {
    const infowindow = new google.maps.InfoWindow();
    
    map = new google.maps.Map(mapElement, {
        center: new google.maps.LatLng(55.4, -4),
        zoom: 6,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        mapId: GMAP_MAPID,
    });

    const data = new google.maps.Data();
    
    data.loadGeoJson(window.gfMapConfig.geojson, null, () => {
        if (typeof window.gfMapConfig.lat === "undefined") {
            fitMapToBounds(data);
        }
        
        addMapLegend();
    });

    data.setStyle((feature) => getFeatureStyle(feature));
    data.addListener("click", (event) => handleMarkerClick(event, infowindow));
    data.setMap(map);

    if (typeof window.gfMapConfig.lat !== "undefined") {
        move_map(window.gfMapConfig.lat, window.gfMapConfig.lng, window.gfMapConfig.zoom);
    }
}

/**
 * Fit map to show all markers
 * @param {google.maps.Data} data - Map data layer
 */
function fitMapToBounds(data) {
    const bounds = new google.maps.LatLngBounds();
    
    data.forEach((feature) => {
        const geometry = feature.getGeometry();
        geometry.forEachLatLng((latLng) => {
            bounds.extend(latLng);
        });
    });

    google.maps.event.addListenerOnce(map, "bounds_changed", () => {
        const maxZoom = window.gfMapConfig.max_zoom || 15;
        if (map.getZoom() > maxZoom) {
            map.setZoom(maxZoom);
        }
    });

    const padding = { left: 50, right: 50, bottom: 50, top: 50 };
    map.fitBounds(bounds, padding);
    map.panToBounds(bounds);
}

/**
 * Add legend to map if template exists
 */
function addMapLegend() {
    const legendTemplate = document.querySelector("#legendtemplate");
    
    if (legendTemplate) {
        const legendClone = legendTemplate.content.cloneNode(true);
        const legend = legendClone.querySelector("#legend");
        map.controls[google.maps.ControlPosition.LEFT_BOTTOM].push(legend);
        legend.style.display = "block";
    }
}

/**
 * Get style for map feature based on type
 * @param {google.maps.Data.Feature} feature - Map feature
 * @returns {object} Style configuration
 */
function getFeatureStyle(feature) {
    const type = feature.getProperty("type");

    if (type === "lb") {
        return {
            fillColor: "#f7a723",
            fillOpacity: 0.2,
            strokeColor: "#f7a723",
            strokeWeight: 1,
        };
    }

    const markerConfig = {
        f: { colour: "red", size: 34 },
        l: { colour: "yellow", size: 28 },
        d: { colour: "blue", size: 24 },
        b: { colour: "", size: 0 },
    };

    const config = markerConfig[type] || { colour: "", size: 0 };

    return {
        icon: {
            url: `/static/img/mapmarkers/${config.colour}.png`,
            scaledSize: new google.maps.Size(config.size, config.size),
        },
        strokeWeight: 1,
        title: feature.getProperty("name"),
    };
}

/**
 * Handle click on map marker
 * @param {object} event - Click event
 * @param {google.maps.InfoWindow} infowindow - Info window instance
 */
function handleMarkerClick(event, infowindow) {
    const feature = event.feature;
    const type = feature.getProperty("type");

    if (type === "b") {
        return;
    }

    const html = buildInfoWindowContent(feature);
    
    infowindow.setContent(html);
    
    if (event.latLng) {
        infowindow.setPosition(event.latLng);
    }
    
    infowindow.setOptions({
        maxWidth: 250,
        pixelOffset: new google.maps.Size(0, -28),
    });
    
    infowindow.open(map);
}

/**
 * Build HTML content for info window
 * @param {google.maps.Data.Feature} feature - Map feature
 * @returns {string} HTML content
 */
function buildInfoWindowContent(feature) {
    const type = feature.getProperty("type");
    const title = feature.getProperty("name");
    const url = feature.getProperty("url");
    const address = feature.getProperty("address");
    const foodbank = feature.getProperty("foodbank");

    let html = "<div class='infowindow'>";
    html += `<h3>${title}</h3>`;

    if (type !== "f") {
        const typeLabels = {
            l: "Location for",
            d: "Donation point for",
            lb: "Service area for",
        };
        
        const label = typeLabels[type] || "";
        const foodbankSlug = slugify(foodbank);
        
        html += `<p>${label} <a href='/needs/at/${foodbankSlug}/'>${foodbank}</a> Food Bank.</p>`;
    }

    if (address) {
        const formattedAddress = address.replace(/(\r\n|\r|\n)/g, "<br>");
        html += `<address>${formattedAddress}</address>`;
    }

    html += `<a href='${url}' class='button is-info is-small'>More Information</a>`;
    html += "</div>";

    return html;
}