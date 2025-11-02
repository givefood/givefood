# gfapp - Progressive Web App Frontend

A lightweight Progressive Web App (PWA) providing a mobile-optimized interface for finding food banks and donation points at https://www.givefood.org.uk/appfe/

## Overview

gfapp is a streamlined, mobile-first web application designed for quick food bank discovery and donation point lookup. It provides a fast, app-like experience for users on mobile devices who need to find nearby food banks or donation points.

**Live URL**: https://www.givefood.org.uk/appfe/

## Features

### Location-Based Search
- **Geographic Search**: Find food banks and donation points near a location
- **Address Geocoding**: Convert addresses to coordinates automatically
- **Distance Calculation**: Results sorted by proximity
- **Multi-Type Results**: Shows both food bank locations and donation points

### Food Bank Display
- **Food Bank Details**: View comprehensive information about specific food banks
- **Current Needs**: Display current and excess items
- **Contact Information**: Phone, email, and website details
- **Locations**: All distribution points for a food bank
- **Donation Points**: Third-party collection locations

### Mobile Optimization
- **Never Cached**: Always shows fresh data
- **Responsive Design**: Optimized for mobile screens
- **Fast Loading**: Minimal dependencies
- **App-like Experience**: Designed for quick interactions

## URL Structure

### Main Pages
- `/appfe/` - Homepage with search interface
- `/appfe/search/` - Search results page
  - Query params: `?lat_lng=51.5,-0.1` or `?address=London`
- `/appfe/fb/<slug>/` - Food bank detail page
- `/appfe/fb/<slug>/<locslug>/` - Individual location page (not yet implemented)

## Search Functionality

### Search Parameters

The search endpoint accepts either coordinates or an address:

**By Coordinates:**
```
/appfe/search/?lat_lng=51.5074,-0.1278
```

**By Address:**
```
/appfe/search/?address=London
```

### Search Results

Results include up to 20 items combining:
- Food bank locations (from `FoodbankLocation`)
- Donation points (from `FoodbankDonationPoint`)
- Distance calculations for each result
- Photos and URLs for each location

### Result Types

Each result is tagged with a type:
- **location** - Food bank distribution location
- **donationpoint** - Third-party donation collection point

## Technical Details

### Caching Strategy
All views use `@never_cache` decorator to ensure users always see current data, which is critical for food bank needs and location accuracy.

### Geographic Search
Uses Django Earthdistance extension for efficient proximity queries:
- Finds nearest 20 donation points
- Finds nearest 20 food bank locations with donation capability
- Combines and sorts by distance
- Calculates distances in miles for display

### URL Generation
Dynamically generates URLs based on object type:
- Locations link to `/needs/at/<slug>/<locslug>/`
- Donation points link to `/needs/at/<slug>/donationpoint/<dpslug>/`

### Reverse Geocoding
When coordinates are provided without an address, the app uses approximate reverse geocoding to show users where they're searching.

### Templates
Located in `templates/app/`:
- `index.html` - Search form homepage
- `search_results.html` - Search results display
- `foodbank.html` - Food bank detail view
- `page.html` - Base page template
- `map.html` - Map display component

## Data Models Used

The app uses models from the main `givefood` app:
- `Foodbank` - Food bank organizations
- `FoodbankLocation` - Distribution points
- `FoodbankDonationPoint` - Donation collection points

## Integration with Other Apps

### gfwfbn Integration
The app leverages URL patterns from gfwfbn for:
- Food bank location pages
- Donation point pages
- Photo endpoints

### Core Functions
Uses utility functions from `givefood.func`:
- `geocode()` - Address to coordinates conversion
- `approx_rev_geocode()` - Approximate reverse geocoding
- `find_locations()` - Food bank location search
- `miles()` - Distance unit conversion

## Development Notes

### Future Features
- Complete location detail view (`location()` function currently placeholder)
- Enhanced filtering options
- Save favorite locations
- Offline mode support
- Progressive Web App manifest

### Performance Considerations
- No caching ensures data freshness
- Database queries optimized with `select_related()`
- Limited result sets (20 items) for fast loading
- Geographic queries use spatial indexes

## Mobile-First Design

The app is specifically designed for mobile users who need:
- Quick access to nearby donation points
- Up-to-date food bank needs
- Easy navigation to locations
- Minimal data usage
- Fast load times

## Related Apps

- **gfwfbn** - Full-featured "What Food Banks Need" tool
- **gfapi2** - API providing the underlying data
- **givefood** - Core models and utilities
- **gfadmin** - Admin interface for data management

## Contact

For technical questions or feature requests:
- Email: mail@givefood.org.uk
