# gfapi3

**Future API (Version 3)** - Currently in development for future release at https://www.givefood.org.uk/api/3/

## Overview

This is the future version of the Give Food API. It is currently under active development and not yet production-ready. The API will provide enhanced endpoints and features building upon the foundation of API v2.

**Status**: Development / Preview

## Current Features

### Donation Points by Company

The API currently provides a specialized endpoint for querying donation points grouped by retail company.

**GET** `/api/3/donationpoints/company/<slug>/`

Returns all donation points for a specific company (e.g., Tesco, Sainsbury's, Asda), along with their associated food banks and current needs.

**Response Format**: JSON

**Response Fields**:
- `id`: UUID of the donation point
- `name`: Donation point name
- `foodbank`: Object containing:
  - `id`: UUID of the food bank
  - `name`: Food bank name
  - `alt_name`: Alternative name
  - `slug`: URL slug
  - `url`: Website URL
  - `shopping_list_url`: Shopping list URL
  - `phone_number`: Primary phone
  - `secondary_phone_number`: Secondary phone
  - `email`: Contact email
  - `address`: Full address
  - `postcode`: Postcode
  - `country`: Country
  - `lat_lng`: Geographic coordinates
  - `charity_number`: Charity registration number
  - `charity_register_url`: Link to charity register
  - `network`: Food bank network affiliation
  - `need`: Current need object with:
    - `id`: Need identifier
    - `items`: List of needed items
    - `excess`: List of excess items
    - `found`: Timestamp of need discovery
- `address`: Donation point address
- `postcode`: Donation point postcode
- `country`: Donation point country
- `lat_lng`: Donation point coordinates
- `place_id`: Google Places ID
- `store_id`: Retailer's store identifier

## Future Development

API v3 is being developed to provide:
- Improved endpoint organization
- Enhanced data relationships
- Better performance and caching
- Additional features and filters
- More comprehensive documentation

## Technical Details

### URL Configuration
Routes are defined in `urls.py` with the `gfapi3` namespace. All URLs are prefixed with `/api/3/`.

### Data Models
Uses the standard Give Food models:
- `Foodbank` - Food bank organizations
- `FoodbankDonationPoint` - Donation collection points
- `FoodbankChangeLine` - Need items

### Response Format
- All responses are in JSON format
- Uses `application/json` content type
- Returns 404 with error object for unknown companies

## Migration from API v2

Once API v3 is production-ready, migration documentation will be provided. For now, continue using [gfapi2](../gfapi2/) for production applications.

## Related Apps

- **gfapi2** - Current production API (v2)
- **gfapi1** - Deprecated legacy API (v1)
- **gfadmin** - Admin interface for data management
- **givefood** - Core models and utilities

## Contact

For questions about API v3 development or to request features:
- Email: mail@givefood.org.uk
