// Configuration
const IP_GEOLOCATION_URL = "/needs/getlocation/";
const PMTILES_URL = "https://mt.givefood.org.uk/uk.pmtiles";
const OSM_BRIGHT_STYLE = "https://tiles.openfreemap.org/styles/bright";

// DOM Elements
const addressField = document.querySelector("#address_field");
const latLngField = document.querySelector("#lat_lng_field");
const useMyLocationBtn = document.querySelector("#usemylocationbtn");
const addressForm = document.querySelector("#addressform");
const mapElement = document.querySelector("#map");

// Global Variables
let map;
let maplibreLoaded = false;
let maplibreLoading = false;

/**
 * Initialize the page functionality
 */
function init() {
    // Check if MapLibre is already loaded
    if (typeof maplibregl !== 'undefined') {
        maplibreLoaded = true;
        onMapLibreLoaded();
        return;
    }

    if (mapElement) {
        // Lazy load MapLibre when map element is visible
        observeMapElement();
    }

    if (useMyLocationBtn) {
        initLocationButton();
    }
}

/**
 * Observe map element and load MapLibre when it enters viewport
 */
function observeMapElement() {
    // Check if IntersectionObserver is supported
    if (!('IntersectionObserver' in window)) {
        // Fallback: load immediately if IntersectionObserver not supported
        loadMapLibre();
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting && !maplibreLoaded && !maplibreLoading) {
                loadMapLibre();
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
 * Dynamically load MapLibre GL
 */
function loadMapLibre() {
    if (maplibreLoaded || maplibreLoading) {
        return;
    }

    // Check if already loaded
    if (typeof maplibregl !== 'undefined') {
        maplibreLoaded = true;
        onMapLibreLoaded();
        return;
    }

    maplibreLoading = true;

    // Load CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/maplibre-gl@^5.5.0/dist/maplibre-gl.css';
    document.head.appendChild(link);

    // Load JS
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/maplibre-gl@^5.5.0/dist/maplibre-gl.js';
    script.async = true;

    script.onload = () => {
        const checkMapLibre = () => {
            if (typeof maplibregl !== 'undefined') {
                maplibreLoaded = true;
                maplibreLoading = false;
                onMapLibreLoaded();
            } else {
                setTimeout(checkMapLibre, 50);
            }
        };
        checkMapLibre();
    };

    script.onerror = () => {
        console.error('Failed to load MapLibre GL');
        maplibreLoading = false;
    };

    document.head.appendChild(script);
}

/**
 * Called when MapLibre GL has finished loading
 */
function onMapLibreLoaded() {
    if (mapElement) {
        initMap();
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

    map.flyTo({
        center: [lng, lat],
        zoom: zoom
    });

    if (window.gfMapConfig.location_marker === true) {
        // Create a custom marker element for the location
        const el = document.createElement('div');
        el.className = 'location-marker';
        el.style.width = '14px';
        el.style.height = '14px';
        el.style.borderRadius = '50%';
        el.style.backgroundColor = '#4385F4';
        el.style.border = '2px solid #fff';
        el.style.boxShadow = '0 0 4px rgba(0,0,0,0.3)';

        new maplibregl.Marker({element: el})
            .setLngLat([lng, lat])
            .addTo(map);
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
 * Initialize MapLibre Map with food bank locations
 */
async function initMap() {
    map = new maplibregl.Map({
        container: 'map',
        style: OSM_BRIGHT_STYLE,
        center: [-4, 55.4],
        zoom: 6,
        attributionControl: true
    });

    // Add navigation controls
    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    // Define marker layers configuration
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

    map.on('load', async () => {
        // Load marker images
        const orgImg = await map.loadImage('/static/img/mapmarkers/red.png');
        const locImg = await map.loadImage('/static/img/mapmarkers/yellow.png');
        const dpImg = await map.loadImage('/static/img/mapmarkers/blue.png');

        map.addImage('orgmrkr', orgImg.data);
        map.addImage('locmrkr', locImg.data);
        map.addImage('dpmrkr', dpImg.data);

        // Add GeoJSON source
        map.addSource('givefood', {
            type: 'geojson',
            data: window.gfMapConfig.geojson,
        });

        // Add layers for each type
        for (const [layer, props] of Object.entries(layers)) {
            map.addLayer({
                'id': layer,
                'type': 'symbol',
                'source': 'givefood',
                'layout': {
                    'icon-image': props.icon,
                    'icon-size': props.size,
                    'icon-allow-overlap': true,
                },
                'filter': ['==', 'type', props.filter],
            });
        }

        // Fit bounds if no specific location is set
        if (typeof window.gfMapConfig.lat === "undefined") {
            fitMapToBounds();
        } else {
            move_map(window.gfMapConfig.lat, window.gfMapConfig.lng, window.gfMapConfig.zoom);
        }

        addMapLegend();
    });

    // Set up cursor changes on hover
    layerList.forEach(layer => {
        map.on('mouseenter', layer, () => {
            map.getCanvas().style.cursor = 'pointer';
        });

        map.on('mouseleave', layer, () => {
            map.getCanvas().style.cursor = '';
        });

        map.on('click', layer, (e) => {
            handleMarkerClick(e);
        });
    });
}

/**
 * Fit map to show all markers
 */
function fitMapToBounds() {
    const features = map.querySourceFeatures('givefood');
    
    if (features.length === 0) {
        return;
    }

    const bounds = new maplibregl.LngLatBounds();
    
    features.forEach((feature) => {
        if (feature.geometry.type === 'Point') {
            bounds.extend(feature.geometry.coordinates);
        }
    });

    const maxZoom = window.gfMapConfig.max_zoom || 15;
    
    map.fitBounds(bounds, {
        padding: { left: 50, right: 50, bottom: 50, top: 50 },
        maxZoom: maxZoom
    });
}

/**
 * Add legend to map if template exists
 */
function addMapLegend() {
    const legendTemplate = document.querySelector("#legendtemplate");
    
    if (legendTemplate) {
        const legendClone = legendTemplate.content.cloneNode(true);
        const legend = legendClone.querySelector("#legend");
        
        // Create a custom control for the legend
        class LegendControl {
            onAdd(map) {
                this._map = map;
                this._container = legend;
                this._container.style.display = 'block';
                return this._container;
            }

            onRemove() {
                this._container.parentNode.removeChild(this._container);
                this._map = undefined;
            }
        }

        map.addControl(new LegendControl(), 'bottom-left');
    }
}

/**
 * Handle click on map marker
 * @param {object} event - Click event
 */
function handleMarkerClick(event) {
    const feature = event.features[0];
    
    // Check for custom click handler in config
    if (window.gfMapConfig.onClick === 'navigate') {
        handleNavigationClick(event);
        return;
    }
    
    const type = feature.properties.type;

    if (type === "b") {
        return;
    }

    const html = buildInfoWindowContent(feature.properties);
    const coordinates = feature.geometry.coordinates.slice();

    // Ensure that if the map is zoomed out such that multiple
    // copies of the feature are visible, the popup appears
    // over the copy being pointed to.
    while (Math.abs(event.lngLat.lng - coordinates[0]) > 180) {
        coordinates[0] += event.lngLat.lng > coordinates[0] ? 360 : -360;
    }

    new maplibregl.Popup({
        maxWidth: '250px',
        offset: 28
    })
        .setLngLat(coordinates)
        .setHTML(html)
        .addTo(map);
}

/**
 * Handle navigation click for parliamentary constituencies
 * @param {object} event - Click event
 */
function handleNavigationClick(event) {
    const feature = event.features[0];
    const name = feature.properties.PCON24NM;
    if (name) {
        const slug = slugify(name);
        window.location = '/write/to/' + slug + '/';
    }
}

/**
 * Build HTML content for info window
 * @param {object} properties - Feature properties
 * @returns {string} HTML content
 */
function buildInfoWindowContent(properties) {
    const type = properties.type;
    const title = properties.name;
    const url = properties.url;
    const address = properties.address;
    const foodbank = properties.foodbank;

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
