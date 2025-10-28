// ===========================
// Utility Functions
// ===========================

/**
 * Insert a new DOM node after a reference node
 * @param {HTMLElement} newNode - The node to insert
 * @param {HTMLElement} referenceNode - The reference node
 */
function insertAfter(newNode, referenceNode) {
    referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

/**
 * Convert string to title case
 * @param {string} str - The string to convert
 * @returns {string} Title-cased string
 */
function titleCase(str) {
    return str.replace(/\w\S*/g, (txt) => {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
}

/**
 * Convert string to title case with food-specific acronyms
 * @param {string} str - The string to convert
 * @returns {string} Title-cased string with food acronyms
 */
function food_titleCase(str) {
    str = titleCase(str);
    str = str.replace(/Uht/g, "UHT");
    str = str.replace(/Bbq/g, "BBQ");
    str = str.replace(/Spf/g, "SPF");
    return str;
}

/**
 * Convert comma-separated values to newline-separated values
 * @param {string} str - CSV string
 * @returns {string} Newline-separated string
 */
function csvToLines(str) {
    return str.replace(/, /g, "\n");
}

/**
 * Convert string to URL-friendly slug
 * @param {string} str - The string to slugify
 * @returns {string} Slugified string
 */
function slugify(str) {
    str = str.trim().toLowerCase();

    // Remove accents, swap ñ for n, etc
    const from = "àáäâèéëêìíïîòóöôùúüûñç·/_,:;";
    const to = "aaaaeeeeiiiioooouuuunc------";
    for (let i = 0; i < from.length; i++) {
        str = str.replace(new RegExp(from.charAt(i), 'g'), to.charAt(i));
    }

    str = str.replace(/[^a-z0-9 -]/g, '') // remove invalid chars
        .replace(/\s+/g, '-') // collapse whitespace and replace by -
        .replace(/-+/g, '-'); // collapse dashes

    return str;
}

/**
 * Clean up address abbreviations
 * @param {string} str - Address string with abbreviations
 * @returns {string} Address with expanded abbreviations
 */
function address_cleanup(str) {
    const abbreviations = {
        "Rd\n": "Road\n",
        "St\n": "Street\n",
        "Ln\n": "Lane\n",
        "Cl\n": "Close\n",
        "Ave\n": "Avenue\n",
        "Ct\n": "Court\n",
        "Dr\n": "Drive\n",
        "Pl\n": "Place\n"
    };

    Object.entries(abbreviations).forEach(([abbr, full]) => {
        str = str.replace(abbr, full);
    });

    return str;
}

// ===========================
// DOM Element References
// ===========================

const DOM = {
    name_field: document.querySelector("#id_name"),
    lat_lng_field: document.querySelector("#id_lat_lng"),
    place_id_field: document.querySelector("#id_place_id"),
    address_field: document.querySelector("#id_address"),
    postcode_field: document.querySelector("#id_postcode"),
    change_text_field: document.querySelector("#id_change_text"),
    excess_change_text: document.querySelector("#id_excess_change_text"),
    fb_name_field: document.querySelector(".form-new-food-bank #id_name"),
    dp_name_field: document.querySelector(".form-new-donation-point #id_name, .form-edit-donation-point #id_name"),
    loc_name_field: document.querySelector("form[class*='food-bank-location'] #id_name"),
    company_field: document.querySelector("#id_company")
};

// ===========================
// API Configuration
// ===========================

const API_URLS = {
    geolocation: (address) => `https://maps.googleapis.com/maps/api/geocode/json?region=uk&key=${gmap_geocode_key}&address=${encodeURIComponent(address)}`,
    placeSearch: (query) => `/admin/proxy/gmaps/textsearch/?region=uk&key=${gmap_places_key}&query=${encodeURIComponent(query)}`,
    placeDetail: (placeId) => `/admin/proxy/gmaps/placedetails/?region=uk&key=${gmap_places_key}&placeid=${placeId}`,
    staticMap: (latLng) => `https://maps.googleapis.com/maps/api/staticmap?zoom=15&size=300x300&key=${gmap_static_key}&scale=2&center=${latLng}`,
    foodbankApi: (slug) => `/api/2/foodbank/${slug}/`
};

// ===========================
// Helper Functions
// ===========================

/**
 * Create a button element with specified properties
 * @param {string} id - Button ID
 * @param {string} text - Button text
 * @param {string} className - Additional CSS classes
 * @returns {HTMLElement} Button element
 */
function createButton(id, text, className = 'button is-info') {
    const div = document.createElement('div');
    div.innerHTML = `<a href='#' id='${id}' class='extra-form-button ${className}'>${text}</a>`;
    return div;
}

/**
 * Create and insert a map image
 * @param {string} latLng - Latitude and longitude string
 * @param {HTMLElement} referenceElement - Element to insert after
 * @returns {HTMLElement} Map image element
 */
function createMapImage(latLng, referenceElement) {
    const mapImg = document.createElement('img');
    mapImg.src = API_URLS.staticMap(latLng);
    insertAfter(mapImg, referenceElement);
    return mapImg;
}

/**
 * Fetch JSON from a URL using modern fetch API
 * @param {string} url - URL to fetch
 * @returns {Promise<any>} Parsed JSON response
 */
async function fetchJSON(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

/**
 * Set location fields (lat/lng and place_id)
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @param {string} placeId - Google Place ID
 */
function setLocationFields(lat, lng, placeId) {
    const latLng = `${lat},${lng}`;
    DOM.lat_lng_field.value = latLng;
    DOM.place_id_field.value = placeId;
    createMapImage(latLng, DOM.place_id_field);
}

/**
 * Parse and set address fields from formatted address
 * @param {string} formattedAddress - Address from Google Places
 */
function setAddressFields(formattedAddress) {
    let address = address_cleanup(formattedAddress.replace(/, /g, "\n"));
    const postcodeMatch = address.match(/[A-Za-z]{1,2}\d{1,2}(?:\s?(?:\d?\w{2}))?/);
    const postcode = postcodeMatch ? postcodeMatch[0] : '';
    
    if (postcode) {
        address = address.replace(" " + postcode, "");
    }
    
    DOM.address_field.value = address;
    DOM.postcode_field.value = postcode;
}

// ===========================
// Feature Implementations
// ===========================

/**
 * Initialize company field auto-selection
 */
function initCompanyAutoSelect() {
    if (!DOM.company_field || !DOM.dp_name_field) return;

    DOM.dp_name_field.addEventListener("keyup", () => {
        for (let i = 0; i < DOM.company_field.options.length; i++) {
            if (DOM.dp_name_field.value.includes(DOM.company_field.options[i].value)) {
                DOM.company_field.options[i].selected = true;
            }
        }
    });
}

/**
 * Initialize food bank name duplicate checker
 */
function initFoodBankNameChecker() {
    if (!DOM.fb_name_field) return;

    const fbNameDupe = document.createElement('div');
    insertAfter(fbNameDupe, DOM.fb_name_field);

    DOM.fb_name_field.addEventListener("keyup", async () => {
        const fbName = DOM.fb_name_field.value;
        const fbSlug = slugify(fbName);
        const apiUrl = API_URLS.foodbankApi(fbSlug);

        try {
            const response = await fetch(apiUrl);
            if (response.status === 404) {
                fbNameDupe.className = "notification is-success";
                fbNameDupe.innerHTML = `No food bank with the name '${fbName}'`;
            } else if (response.status === 200) {
                fbNameDupe.className = "notification is-warning";
                fbNameDupe.innerHTML = `'${fbName}' food bank already exists`;
            }
        } catch (error) {
            console.error('Error checking food bank name:', error);
        }
    });
}

/**
 * Initialize donation point lookup functionality
 */
function initDonationPointLookup() {
    if (!DOM.dp_name_field) return;

    const dpLookupBtn = createButton('dp_lookup_btn', 'Lookup Donation Point');
    insertAfter(dpLookupBtn, DOM.dp_name_field);

    dpLookupBtn.addEventListener("click", async (event) => {
        event.preventDefault();

        try {
            const address = `${DOM.name_field.value}, UK`;
            const placeData = await fetchJSON(API_URLS.placeSearch(address));

            if (!placeData.results || placeData.results.length === 0) {
                console.error('No results found');
                return;
            }

            const location = placeData.results[0].geometry.location;
            const placeId = placeData.results[0].place_id;

            setLocationFields(location.lat, location.lng, placeId);

            // Fetch place details
            const placeDetails = await fetchJSON(API_URLS.placeDetail(placeId));
            const result = placeDetails.result;

            setAddressFields(result.formatted_address);

            if (result.formatted_phone_number) {
                document.querySelector("#id_phone_number").value = result.formatted_phone_number;
            }

            if (result.website) {
                document.querySelector("#id_url").value = result.website;
            }

            if (result.opening_hours && result.opening_hours.weekday_text) {
                document.querySelector("#id_opening_hours").value = result.opening_hours.weekday_text.join("\n");
            }

            if (result.wheelchair_accessible_entrance !== undefined) {
                document.querySelector("#id_wheelchair_accessible").value = result.wheelchair_accessible_entrance;
            }
        } catch (error) {
            console.error('Error looking up donation point:', error);
            alert('Error looking up donation point. Please try again.');
        }
    });
}

/**
 * Initialize location lookup functionality
 */
function initLocationLookup() {
    if (!DOM.loc_name_field) return;

    const locLookupBtn = createButton('loc_lookup_btn', 'Lookup Location');
    insertAfter(locLookupBtn, DOM.loc_name_field);

    locLookupBtn.addEventListener("click", async (event) => {
        event.preventDefault();

        try {
            const address = `${DOM.name_field.value}, UK`;
            const placeData = await fetchJSON(API_URLS.placeSearch(address));

            if (!placeData.results || placeData.results.length === 0) {
                console.error('No results found');
                return;
            }

            const location = placeData.results[0].geometry.location;
            const placeId = placeData.results[0].place_id;

            setLocationFields(location.lat, location.lng, placeId);

            // Fetch place details
            const placeDetails = await fetchJSON(API_URLS.placeDetail(placeId));
            const result = placeDetails.result;

            setAddressFields(result.formatted_address);

            // Location model has phone_number and email fields that can be filled
            if (result.formatted_phone_number) {
                const phoneField = document.querySelector("#id_phone_number");
                if (phoneField) {
                    phoneField.value = result.formatted_phone_number;
                }
            }
        } catch (error) {
            console.error('Error looking up location:', error);
            alert('Error looking up location. Please try again.');
        }
    });
}

/**
 * Initialize lat/lng and place ID lookup functionality
 */
function initLatLngLookup() {
    if (!DOM.lat_lng_field) return;

    const getLatLngBtn = createButton('get_latlng_btn', 'Get Lat/Lng &amp; Place ID');
    insertAfter(getLatLngBtn, DOM.lat_lng_field);

    // Get the button element from the created div
    const latlngBtn = getLatLngBtn.querySelector("#get_latlng_btn");
    latlngBtn.addEventListener("click", async (event) => {
        event.preventDefault();

        try {
            const addressParts = [
                DOM.name_field.value,
                DOM.address_field.value.replace(/\n/g, ", "),
                DOM.postcode_field.value
            ];
            const address = addressParts.join(", ");

            const data = await fetchJSON(API_URLS.geolocation(address));

            if (!data.results || data.results.length === 0) {
                console.error('No results found');
                alert('No location found for this address. Please check the address and try again.');
                return;
            }

            const location = data.results[0].geometry.location;
            const placeId = data.results[0].place_id;

            setLocationFields(location.lat, location.lng, placeId);
        } catch (error) {
            console.error('Error getting lat/lng:', error);
            alert('Error getting location. Please try again.');
        }
    });
}

/**
 * Initialize change text manipulation buttons
 */
function initChangeTextButtons() {
    if (!DOM.change_text_field) return;

    const titlecaseBtn = createButton('titlecase_btn', 'Make Titlecase');
    const csvlineBtn = createButton('csvline_btn', 'CSV to Lines');
    const findreplaceBtn = createButton('findreplace_btn', 'Find & Replace');

    insertAfter(csvlineBtn, DOM.change_text_field);
    insertAfter(findreplaceBtn, DOM.change_text_field);
    insertAfter(titlecaseBtn, DOM.excess_change_text);

    document.querySelector("#titlecase_btn").addEventListener("click", (event) => {
        event.preventDefault();
        DOM.change_text_field.value = food_titleCase(DOM.change_text_field.value);
        DOM.excess_change_text.value = food_titleCase(DOM.excess_change_text.value);
    });

    document.querySelector("#csvline_btn").addEventListener("click", (event) => {
        event.preventDefault();
        DOM.change_text_field.value = csvToLines(DOM.change_text_field.value);
    });

    document.querySelector("#findreplace_btn").addEventListener("click", (event) => {
        event.preventDefault();
        const findText = prompt("Find what?");
        if (findText === null) return; // User cancelled
        
        const replaceText = prompt("Replace with what?");
        if (replaceText === null) return; // User cancelled

        // Use regex replace for broader browser compatibility
        const escapedFindText = findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(escapedFindText, 'g');
        DOM.change_text_field.value = DOM.change_text_field.value.replace(regex, replaceText);
    });
}

// ===========================
// Initialization
// ===========================

/**
 * Initialize all admin features when DOM is ready
 */
function initAdmin() {
    initCompanyAutoSelect();
    initFoodBankNameChecker();
    initDonationPointLookup();
    initLocationLookup();
    initLatLngLookup();
    initChangeTextButtons();
}

// Run initialization
initAdmin();