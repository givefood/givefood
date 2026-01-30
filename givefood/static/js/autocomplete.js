// Address autocomplete functionality for Give Food

// Autocomplete Variables
let autocompleteDropdown = null;
let autocompleteTimeout = null;
let autocompleteAbortController = null;

/**
 * Initialize address autocomplete on page load
 */
function initAutocomplete() {
    const addressField = document.querySelector("#address_field");
    if (addressField) {
        initAddressAutocomplete(addressField);
    }
}

/**
 * Initialize address autocomplete functionality
 * @param {HTMLElement} addressField - The address input field
 */
function initAddressAutocomplete(addressField) {
    const latLngField = document.querySelector("#lat_lng_field");
    
    // Prevent duplicate initialization
    if (document.getElementById('autocomplete-dropdown')) {
        return;
    }

    // Create autocomplete dropdown container with ARIA attributes
    autocompleteDropdown = document.createElement('div');
    autocompleteDropdown.id = 'autocomplete-dropdown';
    autocompleteDropdown.className = 'autocomplete-dropdown';
    autocompleteDropdown.setAttribute('role', 'listbox');
    autocompleteDropdown.setAttribute('aria-label', 'Address suggestions');
    addressField.parentNode.insertBefore(autocompleteDropdown, addressField.nextSibling);

    // Add ARIA attributes to address field
    addressField.setAttribute('role', 'combobox');
    addressField.setAttribute('aria-autocomplete', 'list');
    addressField.setAttribute('aria-expanded', 'false');
    addressField.setAttribute('aria-controls', 'autocomplete-dropdown');

    // Add input event listener with debounce
    addressField.addEventListener('input', (event) => {
        const query = event.target.value.trim();

        // Clear any pending timeout
        if (autocompleteTimeout) {
            clearTimeout(autocompleteTimeout);
        }

        // Cancel any pending fetch request
        if (autocompleteAbortController) {
            autocompleteAbortController.abort();
        }

        // Clear lat_lng field when user types
        if (latLngField) {
            latLngField.value = '';
        }

        // Only search if query has more than 2 characters
        if (query.length > 2) {
            autocompleteTimeout = setTimeout(() => {
                fetchAutocomplete(query, addressField, latLngField);
            }, 200);
        } else {
            hideAutocomplete(addressField);
        }
    });

    // Handle keyboard navigation
    addressField.addEventListener('keydown', (event) => handleAutocompleteKeydown(event, addressField, latLngField));

    // Hide autocomplete when clicking outside
    document.addEventListener('click', (event) => {
        if (addressField && autocompleteDropdown && 
            !addressField.contains(event.target) && 
            !autocompleteDropdown.contains(event.target)) {
            hideAutocomplete(addressField);
        }
    });
}

/**
 * Format an autocomplete item for display
 * @param {Object} item - The item to format
 * @returns {string} Formatted display string
 */
function formatAutocompleteItem(item) {
    if (item.t === 'p') {
        return `${item.n}, ${item.c}`;
    }
    return item.n;
}

/**
 * Fetch autocomplete suggestions from the API
 * @param {string} query - Search query
 * @param {HTMLElement} addressField - The address input field
 * @param {HTMLElement} latLngField - The lat/lng hidden field
 */
async function fetchAutocomplete(query, addressField, latLngField) {
    // Cancel any pending request
    if (autocompleteAbortController) {
        autocompleteAbortController.abort();
    }
    
    // Create new abort controller for this request
    autocompleteAbortController = new AbortController();
    
    try {
        const response = await fetch(`/aac/?q=${encodeURIComponent(query)}`, {
            signal: autocompleteAbortController.signal
        });
        if (!response.ok) {
            hideAutocomplete(addressField);
            return;
        }

        const results = await response.json();
        displayAutocomplete(results, addressField, latLngField);
    } catch (error) {
        // Ignore abort errors
        if (error.name === 'AbortError') {
            return;
        }
        console.warn('Autocomplete fetch failed:', error);
        hideAutocomplete(addressField);
    }
}

/**
 * Display autocomplete suggestions
 * @param {Array} results - Array of autocomplete results
 * @param {HTMLElement} addressField - The address input field
 * @param {HTMLElement} latLngField - The lat/lng hidden field
 */
function displayAutocomplete(results, addressField, latLngField) {
    if (!results || results.length === 0) {
        hideAutocomplete(addressField);
        return;
    }

    // Clear existing items
    autocompleteDropdown.innerHTML = '';

    // Filter valid results and display
    const validResults = results.filter(item => item && item.n && item.l);
    
    if (validResults.length === 0) {
        hideAutocomplete(addressField);
        return;
    }

    validResults.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'autocomplete-item';
        div.id = `autocomplete-item-${index}`;
        div.setAttribute('role', 'option');
        div.setAttribute('data-index', index);
        div.setAttribute('data-lat-lng', item.l);
        
        // Format with county in a span for styling
        if (item.t === 'p') {
            const nameSpan = document.createElement('span');
            nameSpan.textContent = item.n;
            const countySpan = document.createElement('span');
            countySpan.className = 'autocomplete-county';
            countySpan.textContent = `, ${item.c}`;
            div.appendChild(nameSpan);
            div.appendChild(countySpan);
        } else {
            div.textContent = item.n;
        }

        div.addEventListener('click', () => selectAutocompleteItem(item, addressField, latLngField));
        div.addEventListener('mouseenter', () => {
            setActiveAutocompleteItem(index, addressField);
        });

        autocompleteDropdown.appendChild(div);
    });

    autocompleteDropdown.style.display = 'block';
    addressField.setAttribute('aria-expanded', 'true');
}

/**
 * Hide autocomplete dropdown
 * @param {HTMLElement} addressField - The address input field
 */
function hideAutocomplete(addressField) {
    if (autocompleteDropdown) {
        autocompleteDropdown.style.display = 'none';
        autocompleteDropdown.innerHTML = '';
    }
    if (addressField) {
        addressField.setAttribute('aria-expanded', 'false');
        addressField.removeAttribute('aria-activedescendant');
    }
}

/**
 * Set the active autocomplete item
 * @param {number} index - Index of the item to activate
 * @param {HTMLElement} addressField - The address input field
 */
function setActiveAutocompleteItem(index, addressField) {
    const items = autocompleteDropdown.querySelectorAll('.autocomplete-item');
    items.forEach((el, i) => {
        if (i === index) {
            el.classList.add('active');
            el.setAttribute('aria-selected', 'true');
            addressField.setAttribute('aria-activedescendant', el.id);
        } else {
            el.classList.remove('active');
            el.setAttribute('aria-selected', 'false');
        }
    });
}

/**
 * Select an autocomplete item
 * @param {Object} item - The selected item
 * @param {HTMLElement} addressField - The address input field
 * @param {HTMLElement} latLngField - The lat/lng hidden field
 */
function selectAutocompleteItem(item, addressField, latLngField) {
    // Set address field value using shared formatting function
    addressField.value = formatAutocompleteItem(item);

    // Set lat_lng field
    if (latLngField) {
        latLngField.value = item.l;
    }

    hideAutocomplete(addressField);
}

/**
 * Handle keyboard navigation in autocomplete
 * @param {KeyboardEvent} event - Keyboard event
 * @param {HTMLElement} addressField - The address input field
 * @param {HTMLElement} latLngField - The lat/lng hidden field
 */
function handleAutocompleteKeydown(event, addressField, latLngField) {
    if (!autocompleteDropdown || autocompleteDropdown.style.display === 'none') {
        return;
    }

    const items = autocompleteDropdown.querySelectorAll('.autocomplete-item');
    if (items.length === 0) return;

    const activeItem = autocompleteDropdown.querySelector('.autocomplete-item.active');
    let activeIndex = activeItem ? parseInt(activeItem.getAttribute('data-index')) : -1;

    switch (event.key) {
        case 'ArrowDown':
            event.preventDefault();
            // If no selection, go to first item; otherwise go to next
            if (activeIndex === -1) {
                activeIndex = 0;
            } else {
                activeIndex = Math.min(activeIndex + 1, items.length - 1);
            }
            break;
        case 'ArrowUp':
            event.preventDefault();
            // If no selection or at first item, do nothing
            if (activeIndex <= 0) {
                return;
            }
            activeIndex = activeIndex - 1;
            break;
        case 'Enter':
            if (activeItem) {
                event.preventDefault();
                const latLng = activeItem.getAttribute('data-lat-lng');
                const text = activeItem.textContent;
                addressField.value = text;
                if (latLngField) {
                    latLngField.value = latLng;
                }
                hideAutocomplete(addressField);
            }
            return;
        case 'Escape':
            hideAutocomplete(addressField);
            return;
        default:
            return;
    }

    // Update active state using shared function
    setActiveAutocompleteItem(activeIndex, addressField);
}
