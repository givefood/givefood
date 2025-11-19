const foodbank_geojson_url = "/api/2/foodbanks/?format=geojson"
const location_geojson_url = "/api/2/locations/?format=geojson"

var map_main

function move_map(lat, lng) {
    map_main.flyTo({
        center: [lng, lat],
        zoom: 12
    });
}

function add_potential_marker(lat, lng, the_name) {
    const el = document.createElement('div');
    el.className = 'potential-marker';
    el.style.width = '24px';
    el.style.height = '24px';
    el.style.borderRadius = '50% 50% 50% 0';
    el.style.backgroundColor = '#5384ED';
    el.style.border = '2px solid #ffffff';
    el.style.transform = 'rotate(-45deg)';
    el.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';

    new maplibregl.Marker({element: el})
        .setLngLat([lng, lat])
        .setPopup(new maplibregl.Popup().setText(the_name))
        .addTo(map_main);
}

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
        map_main = new maplibregl.Map({
            container: 'map',
            style: 'https://tiles.openfreemap.org/styles/bright',
            center: [-4, 55],
            zoom: 6
        });

        map_main.addControl(new maplibregl.NavigationControl(), 'top-right');

        map_main.on('load', async () => {
            // Add foodbanks source
            map_main.addSource('foodbanks', {
                type: 'geojson',
                data: foodbank_geojson_url
            });

            // Add locations source
            map_main.addSource('locations', {
                type: 'geojson',
                data: location_geojson_url
            });

            // Load marker images
            const redImg = await map_main.loadImage('/static/img/mapmarkers/red.png');
            const yellowImg = await map_main.loadImage('/static/img/mapmarkers/yellow.png');

            map_main.addImage('red-marker', redImg.data);
            map_main.addImage('yellow-marker', yellowImg.data);

            // Add foodbanks layer
            map_main.addLayer({
                'id': 'foodbanks-layer',
                'type': 'symbol',
                'source': 'foodbanks',
                'layout': {
                    'icon-image': 'red-marker',
                    'icon-size': 0.25,
                    'icon-allow-overlap': true
                }
            });

            // Add locations layer
            map_main.addLayer({
                'id': 'locations-layer',
                'type': 'symbol',
                'source': 'locations',
                'layout': {
                    'icon-image': 'yellow-marker',
                    'icon-size': 0.2,
                    'icon-allow-overlap': true
                }
            });

            // Handle clicks on both layers
            ['foodbanks-layer', 'locations-layer'].forEach(layer => {
                map_main.on('click', layer, (e) => {
                    const url = e.features[0].properties.url;
                    window.location = url.replace("https://www.givefood.org.uk", "");
                });

                map_main.on('mouseenter', layer, () => {
                    map_main.getCanvas().style.cursor = 'pointer';
                });

                map_main.on('mouseleave', layer, () => {
                    map_main.getCanvas().style.cursor = '';
                });
            });

            // Move to initial location if provided
            if (typeof initial_lat_lng !== 'undefined') {
                const split_lat_lng = initial_lat_lng.split(",");
                const lat = parseFloat(split_lat_lng[0]);
                const lng = parseFloat(split_lat_lng[1]);
                move_map(lat, lng);
            }

            // Add potential markers
            document.querySelectorAll("#results li").forEach((li) => {
                const lat = parseFloat(li.dataset.lat);
                const lng = parseFloat(li.dataset.lng);
                const the_name = li.dataset.name;
                add_potential_marker(lat, lng, the_name);
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
