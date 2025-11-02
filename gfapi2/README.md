# gfapi2

The current production API (version 2) for Give Food at https://www.givefood.org.uk/api/

## Overview

This is the current production API (version 2) for Give Food, providing access to the largest public database of UK food banks and their current needs.

The API serves food bank data to governments, councils, universities, supermarkets, political parties, the NHS, broadcasters, food manufacturers, hundreds of national & local news websites, and apps.

## Features

- **Multiple Formats**: JSON, XML, YAML, and GeoJSON support
- **Geographic Search**: Find food banks by location or address
- **Real-time Needs**: Current food bank requirements and excess items
- **Political Data**: Parliamentary constituency information for each location
- **Comprehensive Coverage**: Nearly 3000 food bank locations across the UK
- **Caching**: Aggressive caching for performance (ranging from hourly to monthly)
- **CORS Enabled**: Cross-origin requests allowed

## URL Structure

### Documentation & Index
- `/api/2/` - API index page
- `/api/2/docs/` - Interactive API documentation

### Food Banks
- `/api/2/foodbanks/` - List all food banks (supports `?format=json|xml|yaml|geojson`)
- `/api/2/foodbank/<slug>/` - Get details for a specific food bank
- `/api/2/foodbanks/search/` - Search food banks by location
  - Query params: `?lat_lng=51.178889,-1.826111` or `?address=Bexhill-on-Sea`

### Locations (Distribution Points)
- `/api/2/locations/` - List all food bank locations
- `/api/2/locations/search/` - Search locations by coordinates or address
  - Query params: `?lat_lng=52.090833,0.131944` or `?address=ZE2 9AU`

### Donation Points
- `/api/2/donationpoints/` - Get all donation points (GeoJSON only)

### Needs
- `/api/2/needs/` - List recent food bank needs (last 100)
- `/api/2/need/<uuid>/` - Get details for a specific need update

### Political Data
- `/api/2/constituencies/` - List all UK parliamentary constituencies
- `/api/2/constituency/<slug>/` - Get food banks in a specific constituency (supports GeoJSON)

## Response Formats

Add `?format=<format>` to endpoints to specify response format:

- **json** (default for most endpoints)
- **xml** - XML format with proper element naming
- **yaml** - YAML format
- **geojson** - GeoJSON format (for geographic endpoints)

Example:
```
/api/2/foodbanks/?format=geojson
/api/2/foodbank/kingsbridge/?format=yaml
```

## Key Functions

### Views (`views.py`)
- `index()` - API landing page with dump links
- `docs()` - Interactive documentation with examples
- `foodbanks()` - List all open food banks
- `foodbank(slug)` - Individual food bank details with locations, needs, and nearby food banks
- `foodbank_search()` - Geographic search for food banks
- `locations()` - List all distribution locations
- `location_search()` - Geographic search for locations
- `donationpoints()` - List donation points
- `needs()` - Recent needs updates
- `need(id)` - Specific need details
- `constituencies()` - Parliamentary constituencies
- `constituency(slug)` - Food banks in a constituency

### Helper Functions (`func.py`)
- `ApiResponse(data, obj_name, format)` - Formats and returns API responses with CORS headers
- `xml_item_name(plural)` - Maps plural XML element names to singular

## Cache Strategy

The app uses Django's `@cache_page` decorator with different cache times:

- **Monthly** (`SECONDS_IN_MONTH`): Individual food banks, locations
- **Weekly** (`SECONDS_IN_WEEK`): Food bank lists, constituencies, donation points
- **Daily** (`SECONDS_IN_DAY`): Needs, searches, index
- **Hourly** (`SECONDS_IN_HOUR`): Recent needs list

## Data Models

The API uses the following models from `givefood.models`:

- `Foodbank` - Main food bank organizations
- `FoodbankDonationPoint` - Donation collection points
- `FoodbankChange` - Historical needs changes
- `ParliamentaryConstituency` - UK constituency data

## Testing

Tests are located in `tests.py` and cover:

- API index and documentation accessibility
- Multiple format support (JSON, XML, GeoJSON)
- Endpoint accessibility

Run tests:
```bash
pytest gfapi2/tests.py -v
```

## API Rules & Guidelines

When using this API:

1. **Do good** with the data and credit Give Food with a link
2. Keep information up to date (data changes multiple times per day)
3. Link to food banks when displaying their details
4. Don't modify or reorder lists of needed items
5. Link to shopping list URLs when possible for nuance
6. Don't bulk email/call/message the returned contact information

## Contact

For technical questions, optimizations, or to let us know about your project:
- Email: mail@givefood.org.uk
- API Status: https://uptime.givefood.org.uk/

## Related

- **API v1** (deprecated): `/api/1/` (gfapi1 app)
- **API v3** (future): `/api/3/` (gfapi3 app)
- **Data Dumps**: https://www.givefood.org.uk/dumps/
- **GitHub Data**: https://github.com/givefood/data
