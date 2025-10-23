# Give Food Admin Interface

The admin tool for managing Give Food's food bank database, available at https://www.givefood.org.uk/admin/

## Overview

gfadmin is the administrative interface for the Give Food charity, providing staff with tools to manage the UK's largest publicly available database of food banks and their needs. This app handles data entry, verification, publication, and monitoring across nearly 3000 food bank locations.

## Key Features

### Food Bank Management
- Create, edit, and delete food banks
- Manage food bank locations and donation points
- Track food bank networks (Trussell, IFAN, etc.)
- Handle charity registration information
- Update contact details and URLs
- Manage political/constituency data

### Needs Management
- Review and publish food bank need updates
- Categorize items by type (food, toiletries, household, etc.)
- Translate needs into multiple languages
- Send notifications to subscribers
- Track need history and changes
- Handle non-pertinent updates

### Order Management
- Create and track food deliveries to food banks
- Record order details (items, weight, calories, cost)
- Send delivery notifications
- Export order data to CSV
- Group orders for reporting

### Data Quality Tools
- Identify duplicate postcodes
- Find food banks without recent needs
- Monitor data discrepancies
- Track editing activity
- View crawl/scraping results

### Search & Discovery
- Search across food banks, locations, and donation points
- Find food banks by name, address, postcode, or URL
- Search needs by content
- Locate parliamentary constituencies

### Integration & Automation
- Web crawler management for food bank websites
- RSS feed monitoring for food bank news
- Google Maps integration for location data
- Email notification system
- Cache management

### Statistics & Reporting
- Quarterly delivery statistics
- Editing activity metrics
- Subscription growth tracking
- Need categorization analytics
- Food finder usage stats

### Settings & Configuration
- Manage API credentials
- Configure order groups
- Manage food bank groups/networks
- Handle subscriber lists
- View and manage changelog

## Main Sections

### Dashboard (`/admin/`)
The main admin landing page showing:
- Unpublished needs requiring review
- Recent published needs
- New discrepancies
- Key statistics (edits, subscriptions, crawls)
- Recent food bank news articles

### Food Banks (`/admin/foodbanks/`)
- Sortable list of all food banks
- CSV export functionality
- Duplicate postcode detection

### Needs (`/admin/needs/`)
- List of all food bank needs
- Filtering by categorization status
- Bulk operations

### Orders (`/admin/orders/`)
- Delivery tracking
- Order statistics
- CSV export

### Locations (`/admin/locations/`)
- Food bank location management
- Geolocation updates

### Donation Points (`/admin/donationpoints/`)
- Collection point management
- Photo uploads via CloudFlare R2

### Politics (`/admin/politics/`)
- Parliamentary constituency data
- MP information
- Political boundary management

### Finder (`/admin/finder/`)
- Google Places integration
- Identify potential new food banks
- Match against existing database

### Statistics (`/admin/stats/`)
- Various reporting dashboards
- Quarter statistics
- Subscriber graphs

## Technical Details

### URL Configuration
Routes are defined in `urls.py` with the `admin` namespace. All URLs are prefixed with `/admin/`.

### Context Processors
`context_processors.py` provides Google Maps API keys and configuration to all admin templates.

### Templates
Located in `templates/admin/`, using Django template language with Bulma CSS framework.

### Access Control
Protected by the `LoginRequiredAccess` middleware - authentication required for all admin pages.

### Key Models Used
- `Foodbank` - Core food bank data
- `FoodbankLocation` - Physical locations
- `FoodbankDonationPoint` - Collection points
- `FoodbankChange` - Need updates
- `FoodbankChangeLine` - Individual need items
- `Order` - Food deliveries
- `ParliamentaryConstituency` - Political data
- `FoodbankSubscriber` - Email subscriptions
- `CrawlSet` / `CrawlItem` - Web scraping results

## Development Notes

- All forms use Django's model forms for validation
- CSV exports use Django's CSV writer
- Email templates located in `templates/admin/emails/`
- Supports bulk operations via POST requests
- Uses Django cache framework for performance
- Integrates with external APIs (Google Maps, etc.)

## Related Apps

- **gfoffline** - Background tasks and scheduled jobs
- **gfapi2** - Public API serving the data
- **gfwfbn** - Public-facing "What Food Banks Need" tool
- **gfdash** - Public dashboards for food bank networks
