// MapLibre-based map functionality for Give Food
// Replaces the previous Google Maps implementation

// DOM Elements
const addressField = document.querySelector("#address_field");
const latLngField = document.querySelector("#lat_lng_field");
const useMyLocationBtn = document.querySelector("#usemylocationbtn");
const addressForm = document.querySelector("#addressform");
const mapElement = document.querySelector("#map");

// Global Variables
let map;
let currentPopup = null;

// Layer configuration for different marker types
const layers = {
    'donationpoints': {
        'icon': 'dpmrkr',
        'size': 0.15,
        'filter': 'd',
    },
    'locations': {
        'icon': 'locmrkr',
        'size': 0.2,
        'filter': 'l',
    },
    'foodbanks': {
        'icon': 'orgmrkr',
        'size': 0.25,
        'filter': 'f',
    },
};
const layerList = Object.keys(layers);

/**
 * Initialize the page functionality
 */
function init() {
    if (mapElement && typeof window.gfMapConfig !== 'undefined') {
        initMap();
    }

    if (useMyLocationBtn) {
        initLocationButton();
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
                if (addressField) {
                    addressField.value = "";
                }
                window.location = `${url}?lat_lng=${lat},${lng}`;
            });
        }
    });
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
 * Initialize MapLibre map with food bank locations
 */
function initMap() {
    const config = window.gfMapConfig;
    
    // Determine initial center and zoom
    // Use hasPosition to check if we should use a fixed position or fit to bounds later
    const hasPosition = typeof config.lat !== "undefined" && typeof config.lng !== "undefined";
    // Default center is UK, default zoom is 5 to show the whole UK
    const initialCenter = hasPosition ? [parseFloat(config.lng), parseFloat(config.lat)] : [-4, 55.4];
    const initialZoom = hasPosition ? (config.zoom || 13) : 5;
    
    map = new maplibregl.Map({
        container: 'map',
        style: 'https://tiles.openfreemap.org/styles/bright',
        center: initialCenter,
        zoom: initialZoom,
        attributionControl: false, // Disable default attribution
    });

    // Add compact attribution control (collapsed by default)
    map.addControl(new maplibregl.AttributionControl({
        compact: true,
    }));

    // Add navigation controls
    const nav = new maplibregl.NavigationControl();
    map.addControl(nav, 'top-right');

    map.on('load', async () => {
        // Load marker images
        const orgimg = await map.loadImage('/static/img/mapmarkers/red.png');
        const locimg = await map.loadImage('/static/img/mapmarkers/yellow.png');
        const dpimg = await map.loadImage('/static/img/mapmarkers/blue.png');

        map.addImage('orgmrkr', orgimg.data);
        map.addImage('locmrkr', locimg.data);
        map.addImage('dpmrkr', dpimg.data);

        // Add GeoJSON source
        map.addSource('givefood', {
            type: 'geojson',
            data: config.geojson,
        });

        // Add layers for each marker type
        for (const [layer, props] of Object.entries(layers)) {
            map.addLayer({
                'id': layer,
                'type': 'symbol',
                'source': 'givefood',
                'layout': {
                    'icon-image': props.icon,
                    'icon-size': props.size,
                    'icon-allow-overlap': true,
                    'text-field': ['step', ['zoom'], '', 12, ['get', 'name']],
                    'text-offset': [1, 0],
                    'text-anchor': 'left',
                    'text-size': 12,
                    'text-max-width': 15,
                    'text-optional': true,
                },
                'paint': {
                    'text-color': '#333',
                    'text-halo-color': '#fff',
                    'text-halo-width': 1,
                },
                'filter': ['==', 'type', props.filter],
            });
        }

        // Add location boundary layer for foodbank location polygons
        map.addLayer({
            'id': 'service-area',
            'type': 'fill',
            'source': 'givefood',
            'paint': {
                'fill-color': '#f7a723',
                'fill-opacity': 0.2,
            },
            'filter': ['==', 'type', 'lb'],
        });

        map.addLayer({
            'id': 'service-area-outline',
            'type': 'line',
            'source': 'givefood',
            'paint': {
                'line-color': '#f7a723',
                'line-width': 1,
            },
            'filter': ['==', 'type', 'lb'],
        });

        // Add parliamentary constituency layer if needed
        map.addLayer({
            'id': 'constituency',
            'type': 'fill',
            'source': 'givefood',
            'paint': {
                'fill-color': '#000',
                'fill-opacity': 0.1,
            },
            'filter': ['has', 'PCON24NM'],
        });

        map.addLayer({
            'id': 'constituency-outline',
            'type': 'line',
            'source': 'givefood',
            'paint': {
                'line-color': '#000',
                'line-width': 1,
            },
            'filter': ['has', 'PCON24NM'],
        });

        // Fit bounds if no initial position specified
        if (!hasPosition) {
            // Use precomputed bounds if available (faster, no extra request)
            if (config.bounds) {
                const bounds = [
                    [config.bounds.west, config.bounds.south],  // SW corner
                    [config.bounds.east, config.bounds.north]   // NE corner
                ];
                const maxZoom = config.max_zoom || 15;
                map.fitBounds(bounds, {
                    padding: 50,
                    maxZoom: maxZoom,
                });
            } else if (config.geojson) {
                // Fall back to fetching GeoJSON for bounds calculation
                fitMapToBoundsFromGeoJSON(config.geojson);
            }
        }

        // Add location marker if configured
        if (hasPosition && config.location_marker === true) {
            addLocationMarker(parseFloat(config.lat), parseFloat(config.lng));
        }

        // Show legend
        addMapLegend();
    });

    // Set cursor to pointer on hover over markers
    map.on('mouseenter', layerList, () => {
        map.getCanvas().style.cursor = 'pointer';
    });

    map.on('mouseleave', layerList, () => {
        map.getCanvas().style.cursor = '';
    });

    // Handle marker clicks
    map.on('click', layerList, (e) => {
        handleMarkerClick(e);
    });

    // Handle constituency clicks for navigation
    map.on('click', 'constituency', (e) => {
        if (config.onClick === 'navigate') {
            const name = e.features[0].properties.PCON24NM;
            if (name) {
                const slug = slugify(name);
                window.location = '/write/to/' + slug + '/';
            }
        }
    });

    // Handle location boundary clicks
    map.on('click', 'service-area', (e) => {
        handleServiceAreaClick(e);
    });

    // Set cursor for location boundary polygons
    map.on('mouseenter', 'service-area', () => {
        map.getCanvas().style.cursor = 'pointer';
    });

    map.on('mouseleave', 'service-area', () => {
        map.getCanvas().style.cursor = '';
    });

    // Set cursor for constituency polygons
    map.on('mouseenter', 'constituency', () => {
        if (config.onClick === 'navigate') {
            map.getCanvas().style.cursor = 'pointer';
        }
    });

    map.on('mouseleave', 'constituency', () => {
        map.getCanvas().style.cursor = '';
    });
}

/**
 * Handle click on location boundary polygon
 * @param {object} e - Click event
 */
function handleServiceAreaClick(e) {
    const properties = e.features[0].properties;
    const name = properties.name;
    const url = properties.url;
    const foodbank = properties.foodbank;

    const html = buildPopupContent(name, 'lb', null, url, foodbank);

    // Close any existing popup
    if (currentPopup) {
        currentPopup.remove();
    }

    // Use click location for popup position (polygon doesn't have a single coordinate)
    currentPopup = new maplibregl.Popup()
        .setLngLat(e.lngLat)
        .setHTML(html)
        .addTo(map);
}

/**
 * Handle click on map marker
 * @param {object} e - Click event
 */
function handleMarkerClick(e) {
    const config = window.gfMapConfig;
    
    // Check for custom click handler in config
    if (config.onClick === 'navigate') {
        handleNavigationClick(e);
        return;
    }

    const coordinates = e.features[0].geometry.coordinates.slice();
    const properties = e.features[0].properties;
    const name = properties.name;
    const type = properties.type;
    const address = properties.address;
    const url = properties.url;
    const foodbank = properties.foodbank;

    // Ensure that if the map is zoomed out such that multiple
    // copies of the feature are visible, the popup appears
    // over the copy being pointed to
    while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
        coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
    }

    const html = buildPopupContent(name, type, address, url, foodbank);

    // Close any existing popup
    if (currentPopup) {
        currentPopup.remove();
    }

    currentPopup = new maplibregl.Popup()
        .setLngLat(coordinates)
        .setHTML(html)
        .addTo(map);
}

/**
 * Handle navigation click for parliamentary constituencies
 * @param {object} e - Click event
 */
function handleNavigationClick(e) {
    const name = e.features[0].properties.PCON24NM;
    if (name) {
        const slug = slugify(name);
        window.location = '/write/to/' + slug + '/';
    }
}

/**
 * Build HTML content for popup
 * @param {string} name - Location name
 * @param {string} type - Location type (f, l, d, lb)
 * @param {string} address - Location address
 * @param {string} url - Location URL
 * @param {string} foodbank - Parent foodbank name
 * @returns {string} HTML content
 */
function buildPopupContent(name, type, address, url, foodbank) {
    let html = "<div class='popup-title'>" + name + "</div>";
    
    if (address) {
        html += "<address>" + address.replace(/(\r\n|\r|\n)/g, '<br>') + "</address>";
    }
    
    if (type !== "f") {
        const foodbankSlug = slugify(foodbank);
        if (type === "l") {
            html += "<p>Part of ";
        } else if (type === "d") {
            html += "<p>Donation point for ";
        } else if (type === "lb") {
            html += "<p>Location boundary for ";
        }
        html += "<a href='/needs/at/" + foodbankSlug + "/'>" + foodbank + "</a> Food Bank.</p>";
    }
    
    html += "<a href='" + url + "' class='button is-info is-small is-light'>More Information</a>";

    return html;
}

/**
 * Fit map to show all markers by fetching GeoJSON directly
 * This is more reliable than querySourceFeatures which only returns visible tiles
 * @param {string} geojsonUrl - URL to the GeoJSON data
 */
async function fitMapToBoundsFromGeoJSON(geojsonUrl) {
    try {
        const response = await fetch(geojsonUrl);
        if (!response.ok) return;
        
        const data = await response.json();
        if (!data.features || data.features.length === 0) return;
        
        const bounds = new maplibregl.LngLatBounds();
        
        data.features.forEach((feature) => {
            if (feature.geometry.type === 'Point') {
                bounds.extend(feature.geometry.coordinates);
            } else if (feature.geometry.type === 'Polygon') {
                feature.geometry.coordinates[0].forEach((coord) => {
                    bounds.extend(coord);
                });
            } else if (feature.geometry.type === 'MultiPolygon') {
                feature.geometry.coordinates.forEach((polygon) => {
                    polygon[0].forEach((coord) => {
                        bounds.extend(coord);
                    });
                });
            }
        });

        if (!bounds.isEmpty()) {
            const maxZoom = window.gfMapConfig.max_zoom || 15;
            map.fitBounds(bounds, {
                padding: 50,
                maxZoom: maxZoom,
            });
        }
    } catch (e) {
        // If fetch fails, use default view
        console.warn('Failed to fetch GeoJSON for bounds calculation:', e);
    }
}

/**
 * Add a location marker for the user's searched location
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 */
function addLocationMarker(lat, lng) {
    // Create a simple circle marker for the user's location
    const el = document.createElement('div');
    el.className = 'location-marker';
    el.style.width = '14px';
    el.style.height = '14px';
    el.style.borderRadius = '50%';
    el.style.backgroundColor = '#4385F4';
    el.style.border = '2px solid #fff';
    el.style.boxShadow = '0 0 4px rgba(0,0,0,0.3)';

    new maplibregl.Marker({ element: el })
        .setLngLat([lng, lat])
        .addTo(map);
}

/**
 * Add legend to map if template exists
 */
function addMapLegend() {
    const legendTemplate = document.querySelector("#legendtemplate");
    
    if (legendTemplate) {
        const legendClone = legendTemplate.content.cloneNode(true);
        const legend = legendClone.querySelector("#legend");
        
        // Append to the map's container element (inside the map div)
        // MapLibre creates a canvas-container inside the map element
        if (mapElement) {
            mapElement.appendChild(legend);
            legend.style.display = 'block';
            legend.style.position = 'absolute';
            legend.style.bottom = '30px';
            legend.style.left = '10px';
            legend.style.zIndex = '1';
        }
    }
}

/**
 * Move map to specified location (for compatibility)
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @param {number} zoom - Zoom level
 */
function move_map(lat, lng, zoom) {
    if (typeof map === "undefined" || !map) {
        return;
    }

    map.flyTo({
        center: [lng, lat],
        zoom: zoom,
    });
}