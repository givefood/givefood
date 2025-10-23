# gfapi1

**DEPRECATED**: This is the first version of the Give Food API. New applications should use [gfapi2](../gfapi2/) instead.

This app provides a RESTful API for accessing food bank data, including locations, needs, and searches. It is available at https://www.givefood.org.uk/api/1/

## Features

- **Food Bank Listings**: Get all food banks in JSON or CSV format
- **Food Bank Search**: Find food banks near a location using geocoding
- **Food Bank Details**: Get detailed information about a specific food bank
- **Needs Tracking**: Access current and historical food bank needs
- **Caching**: All endpoints are cached for performance (1 hour to 1 month depending on the endpoint)

## URL Structure

- `/api/1/` - API index and documentation
- `/api/1/foodbanks/` - List all food banks
- `/api/1/foodbanks/search/` - Search for food banks near a location
- `/api/1/foodbank/<slug>/` - Get details for a specific food bank
- `/api/1/needs/` - List recent food bank needs
- `/api/1/need/<id>/` - Get details for a specific need

## Endpoints

### List Food Banks

**GET** `/api/1/foodbanks/`

Returns all food banks in the database.

**Parameters:**
- `format` (optional): Response format, either `json` (default) or `csv`

**Response Fields:**
- `name`: Food bank name
- `slug`: Unique identifier
- `url`: Food bank website
- `shopping_list_url`: URL to shopping list
- `phone`: Contact phone number
- `email`: Contact email
- `address`: Full address
- `postcode`: Postcode
- `parliamentary_constituency`: Constituency name
- `mp`: Member of Parliament name
- `mp_party`: MP's political party
- `ward`: Electoral ward
- `district`: Local authority district
- `country`: Country (England, Scotland, Wales, Northern Ireland)
- `charity_number`: Registered charity number
- `charity_register_url`: URL to charity register
- `closed`: Whether the food bank is closed
- `latt_long`: Latitude and longitude coordinates
- `network`: Food bank network affiliation
- `self`: API URL for this food bank

**Cache:** 1 month

### Search Food Banks

**GET** `/api/1/foodbanks/search/`

Find the 10 nearest food banks to a given location.

**Parameters:**
- `lattlong` (optional): Latitude and longitude in format "lat,lng"
- `address` (optional): Address to geocode and search from

One of `lattlong` or `address` is required.

**Response Fields:**

All fields from the food bank listing endpoint, plus:
- `distance_m`: Distance in meters
- `distance_mi`: Distance in miles
- `needs`: Current needs as text
- `number_needs`: Number of items needed
- `need_id`: Unique identifier for the need
- `updated`: Timestamp of last need update
- `updated_text`: Human-readable time since update

**Cache:** 1 day

### Get Food Bank Details

**GET** `/api/1/foodbank/<slug>/`

Get detailed information about a specific food bank, including all locations.

**Response Fields:**

All fields from the food bank listing endpoint, plus:
- `needs`: Current needs as text
- `number_needs`: Number of items needed
- `need_found`: Whether needs were found
- `need_id`: Unique identifier for the current need
- `need_self`: API URL for the current need
- `locations`: Array of location objects with:
  - `name`: Location name
  - `address`: Location address
  - `postcode`: Location postcode
  - `latt_long`: Location coordinates
  - `phone`: Location phone number
  - `parliamentary_constituency`: Constituency name
  - `mp`: Member of Parliament name
  - `mp_party`: MP's political party
  - `ward`: Electoral ward
  - `district`: Local authority district
- `updated`: Timestamp of last need update
- `updated_text`: Human-readable time since update

**Cache:** 1 month

### List Needs

**GET** `/api/1/needs/`

Get recent food bank needs.

**Parameters:**
- `limit` (optional): Number of needs to return, either `100` (default) or `1000`

**Response Fields:**
- `id`: Unique need identifier
- `created`: Timestamp of when need was created
- `foodbank_name`: Name of the food bank
- `foodbank_slug`: Slug of the food bank
- `foodbank_self`: API URL for the food bank
- `needs`: Needs as text
- `url`: Source URL for the need
- `self`: API URL for this need

**Cache:** 1 hour

### Get Need Details

**GET** `/api/1/need/<id>/`

Get details for a specific food bank need.

**Response Fields:**
- `id`: Unique need identifier
- `created`: Timestamp of when need was created
- `foodbank_name`: Name of the food bank
- `foodbank_slug`: Slug of the food bank
- `foodbank_self`: API URL for the food bank
- `needs`: Needs as text
- `url`: Source URL for the need
- `self`: API URL for this need

**Cache:** 1 day

## Deprecation Notice

This API version is deprecated and maintained for backwards compatibility only. New features are not being added to this version.

Please use [gfapi2](../gfapi2/) for new applications, which provides:
- Improved endpoint structure
- Additional features and data
- Better documentation
- Active development and support

## Technical Details

- Built with Django views and URL patterns
- Uses Django's cache framework for performance
- Supports JSON and CSV output formats (where applicable)
- Integrates with the main Give Food models (Foodbank, FoodbankChange)
- Uses geographic search via the `find_foodbanks()` helper function
- Geocoding support via the `geocode()` helper function
