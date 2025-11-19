// Constituency map using MapLibre GL
const PARL_CON_GEOJSON_URL = "/static/geojson/parlcon.json";
const OSM_BRIGHT_STYLE = "https://tiles.openfreemap.org/styles/bright";

let map;

/**
 * Convert string to URL-friendly slug
 * @param {string} str - String to slugify
 * @returns {string} Slugified string
 */
function slugify(str) {
    str = str.replace(/^\s+|\s+$/g, '').toLowerCase();

    const from = "àáäâèéëêìíïîòóöôùúüûñç·/_,:;";
    const to = "aaaaeeeeiiiioooouuuunc------";
    
    for (let i = 0; i < from.length; i++) {
        str = str.replace(new RegExp(from.charAt(i), 'g'), to.charAt(i));
    }

    str = str
        .replace(/[^a-z0-9 -]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-');

    return str;
}

/**
 * Initialize constituency map
 */
function init_map() {
    // Load MapLibre CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/maplibre-gl@^5.5.0/dist/maplibre-gl.css';
    document.head.appendChild(link);

    // Load MapLibre JS
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/maplibre-gl@^5.5.0/dist/maplibre-gl.js';
    script.async = false;

    script.onload = () => {
        map = new maplibregl.Map({
            container: 'map',
            style: OSM_BRIGHT_STYLE,
            center: [-4, 55],
            zoom: 6
        });

        map.addControl(new maplibregl.NavigationControl(), 'top-right');

        map.on('load', async () => {
            // Add GeoJSON source
            map.addSource('constituencies', {
                type: 'geojson',
                data: PARL_CON_GEOJSON_URL
            });

            // Add fill layer
            map.addLayer({
                'id': 'constituencies-fill',
                'type': 'fill',
                'source': 'constituencies',
                'paint': {
                    'fill-color': '#000',
                    'fill-opacity': 0.1
                }
            });

            // Add outline layer
            map.addLayer({
                'id': 'constituencies-outline',
                'type': 'line',
                'source': 'constituencies',
                'paint': {
                    'line-color': '#000',
                    'line-width': 1
                }
            });

            // Fit map to bounds of all features
            const data = await fetch(PARL_CON_GEOJSON_URL).then(r => r.json());
            
            if (data.features && data.features.length > 0) {
                const bounds = new maplibregl.LngLatBounds();
                
                data.features.forEach(feature => {
                    if (feature.geometry.type === 'Polygon') {
                        feature.geometry.coordinates[0].forEach(coord => {
                            bounds.extend(coord);
                        });
                    } else if (feature.geometry.type === 'MultiPolygon') {
                        feature.geometry.coordinates.forEach(polygon => {
                            polygon[0].forEach(coord => {
                                bounds.extend(coord);
                            });
                        });
                    }
                });

                map.fitBounds(bounds, { padding: 20 });
            }

            // Change cursor on hover
            map.on('mouseenter', 'constituencies-fill', () => {
                map.getCanvas().style.cursor = 'pointer';
            });

            map.on('mouseleave', 'constituencies-fill', () => {
                map.getCanvas().style.cursor = '';
            });

            // Handle click
            map.on('click', 'constituencies-fill', (e) => {
                const feature = e.features[0];
                const name = feature.properties.PCON24NM;
                if (name) {
                    const slug = slugify(name);
                    window.location = '/needs/in/constituency/' + slug + '/';
                }
            });
        });
    };

    document.head.appendChild(script);
}

// Initialize map when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init_map);
} else {
    init_map();
}
